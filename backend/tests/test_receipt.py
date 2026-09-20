"""Receipt upload validation (§11): types, sizes, empty files and magic
bytes — the OCR itself needs AWS, so those paths end in 503 here."""

import io

# A tiny real 1×1 PNG (magic bytes + minimal structure)
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32 + b"\xff\xd9"
PDF_BYTES = b"%PDF-1.4\n%fake-for-validation\n%%EOF"
SECRET_BYTES = b"MZ\x90\x00" + b"\x00" * 64  # windows exe magic


def _upload(client, headers, data, content_type):
    return client.post(
        "/api/receipt/upload",
        headers=headers,
        files={"file": ("receipt.bin", io.BytesIO(data), content_type)},
    )


class TestUploadValidation:
    def test_unsupported_media_type_415(self, client, auth_headers):
        headers, _ = auth_headers(email="ocr1@example.com")
        response = _upload(client, headers, b"plain text", "text/plain")
        assert response.status_code == 415
        assert "JPEG, PNG or PDF" in response.json()["detail"]

    def test_empty_file_400(self, client, auth_headers):
        headers, _ = auth_headers(email="ocr2@example.com")
        response = _upload(client, headers, b"", "image/png")
        assert response.status_code == 400

    def test_fake_bytes_rejected_even_with_image_mime(self, client, auth_headers):
        """An .exe renamed to .png must not pass validation (§11)."""
        headers, _ = auth_headers(email="ocr3@example.com")
        response = _upload(client, headers, SECRET_BYTES, "image/png")
        assert response.status_code == 400
        assert "not a valid" in response.json()["detail"]

    def test_text_renamed_to_jpeg_rejected(self, client, auth_headers):
        headers, _ = auth_headers(email="ocr4@example.com")
        response = _upload(client, headers, b"just some words", "image/jpeg")
        assert response.status_code == 400

    def test_oversize_file_413(self, client, auth_headers):
        headers, _ = auth_headers(email="ocr5@example.com")
        big = PNG_BYTES + b"\x00" * (5 * 1024 * 1024 + 1)
        response = _upload(client, headers, big, "image/png")
        assert response.status_code == 413

    def test_real_png_and_jpeg_and_pdf_pass_validation_then_503(
        self, client, auth_headers
    ):
        """Without AWS the validated upload fails cloud-side with a clear
        503 (never a stack trace, never a silent 500)."""
        headers, _ = auth_headers(email="ocr6@example.com")
        for data, mime in (
            (PNG_BYTES, "image/png"),
            (JPEG_BYTES, "image/jpeg"),
            (PDF_BYTES, "application/pdf"),
        ):
            response = _upload(client, headers, data, mime)
            assert response.status_code == 503, (mime, response.status_code)
            assert "not configured" in response.json()["detail"]

    def test_mismatched_declared_type_uses_actual_bytes(
        self, client, auth_headers
    ):
        """PNG payload mislabelled as jpeg → accepted & treated as PNG."""
        headers, _ = auth_headers(email="ocr7@example.com")
        response = _upload(client, headers, PNG_BYTES, "image/jpeg")
        assert response.status_code == 503  # passed validation, hit Textract

    def test_upload_requires_auth(self, client):
        response = client.post(
            "/api/receipt/upload",
            files={"file": ("r.png", io.BytesIO(PNG_BYTES), "image/png")},
        )
        assert response.status_code == 401


class TestNormalization:
    def test_quantities_units_and_prices(self):
        from app.services.receipt_normalize import (
            _parse_price,
            normalize_receipt_items,
        )

        items = normalize_receipt_items(
            [
                {"name": "AMUL MILK 1L", "quantity": "2", "price": "130.00"},
                {"name": "FRESH TOMATO 500G", "quantity": "1", "price": "18.50"},
                {"name": "CASH TENDERED", "quantity": None, "price": "200.00"},
            ],
            [],
        )
        by_name = {i.name: i for i in items}
        assert "Milk" in by_name or "Amul Milk" in by_name
        milk = next(v for k, v in by_name.items() if "milk" in k.lower())
        assert milk.unit == "l"
        assert milk.quantity == 2
        assert milk.unit_price == 65.0  # 130 ÷ 2 l
        assert not any("tender" in k.lower() for k in by_name)
        assert _parse_price(None, 1) is None
