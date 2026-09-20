"""Amazon Textract integration — receipt OCR (AnalyzeExpense).

Prefers reading the receipt from S3 (the standard production flow);
falls back to sending raw bytes when no bucket is configured.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TextractUnavailable(Exception):
    pass


@dataclass
class ReceiptExtraction:
    """Raw OCR output handed to the normalisation step."""

    line_items: list[dict] = field(default_factory=list)  # {name, quantity?, price?}
    raw_lines: list[str] = field(default_factory=list)
    vendor: str | None = None
    total: str | None = None


class TextractService:
    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config

                self._client = boto3.client(
                    "textract",
                    region_name=self._settings.aws_region,
                    aws_access_key_id=self._settings.aws_access_key_id,
                    aws_secret_access_key=self._settings.aws_secret_access_key,
                    config=Config(connect_timeout=5, read_timeout=60),
                )
            except Exception as exc:
                raise TextractUnavailable(f"Textract init failed: {exc!r}") from exc
        return self._client

    def analyze_receipt(
        self, *, data: bytes | None = None, s3_key: str | None = None
    ) -> ReceiptExtraction:
        """OCR a receipt either from bytes or from an S3 object."""
        if s3_key and self._settings.aws_s3_bucket:
            document = {
                "S3Object": {
                    "Bucket": self._settings.aws_s3_bucket,
                    "Name": s3_key,
                }
            }
        elif data:
            document = {"Bytes": data}
        else:
            raise TextractUnavailable("No receipt bytes or S3 object supplied")

        try:
            response = self._get_client().analyze_expense(Document=document)
        except Exception as exc:
            logger.warning("Textract analyze_expense failed: %r", exc)
            raise TextractUnavailable(f"OCR failed: {exc!r}") from exc
        return self._parse_expense_response(response)

    @staticmethod
    def _parse_expense_response(response: dict) -> ReceiptExtraction:
        result = ReceiptExtraction()
        docs = response.get("ExpenseDocuments", [])
        for doc in docs:
            for summary_field in doc.get("SummaryFields", []):
                ftype = (summary_field.get("Type") or {}).get("Text", "")
                value = (summary_field.get("ValueDetection") or {}).get("Text", "")
                if ftype == "VENDOR_NAME":
                    result.vendor = value
                elif ftype == "TOTAL":
                    result.total = value

            for group in doc.get("LineItemGroups", []):
                for line_item in group.get("LineItems", []):
                    fields: dict[str, str] = {}
                    for exp_field in line_item.get("LineItemExpenseFields", []):
                        key = (exp_field.get("Type") or {}).get("Text", "")
                        value = (exp_field.get("ValueDetection") or {}).get("Text", "")
                        if key and value:
                            fields[key] = value
                    name = fields.get("ITEM", "").strip()
                    if not name:
                        continue
                    result.line_items.append(
                        {
                            "name": name,
                            "quantity": fields.get("QUANTITY"),
                            "price": fields.get("PRICE"),
                        }
                    )
                    result.raw_lines.append(name)
        return result
