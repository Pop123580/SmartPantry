"""Receipt OCR — multipart upload → S3 → Textract → normalized items.

IMPORTANT (spec): OCR results are RETURNED for user confirmation —
nothing is inserted into the pantry here.
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.dependencies import CurrentUser
from app.schemas.receipt import ReceiptItemOut
from app.services.bedrock_service import BedrockService
from app.services.receipt_normalize import normalize_receipt_items
from app.services.s3_service import S3Service, S3Unavailable
from app.services.textract_service import TextractService, TextractUnavailable

router = APIRouter(prefix="/api/receipt", tags=["receipt"])
logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "application/pdf": "PDF",
}

# Magic bytes per format — the declared Content-Type / filename is NOT
# trusted on its own; the payload must actually look like the type.
MAGIC_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "application/pdf": (b"%PDF-",),
}


def _sniff_format(data: bytes) -> str | None:
    for mime, signatures in MAGIC_SIGNATURES.items():
        if any(data.startswith(sig) for sig in signatures):
            return mime
    return None


@router.post(
    "/upload",
    response_model=list[ReceiptItemOut],
    summary="Upload a receipt photo/PDF for OCR",
    description="Accepts ``multipart/form-data`` with a ``file`` field "
    "(JPEG/PNG/PDF, ≤ 5 MB). The image is archived to Amazon S3, parsed with "
    "Amazon Textract (AnalyzeExpense), and lines are normalized into "
    "``CreatePantryItemDTO[]`` — the frontend confirms them before anything "
    "is added to the pantry.",
    responses={
        400: {"description": "Empty file"},
        401: {"description": "Missing/invalid token"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported media type"},
        503: {"description": "OCR pipeline not configured/available"},
    },
)
async def upload_receipt(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Receipt image (JPEG/PNG) or PDF"),
) -> list[ReceiptItemOut]:
    settings = get_settings()

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. "
            "Use JPEG, PNG or PDF.",
        )

    limit = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file uploaded")
    if len(data) > limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_size_mb} MB limit",
        )

    # Content sniffing — don't trust the extension/declared type alone.
    actual = _sniff_format(data)
    if actual is None or actual not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content is not a valid JPEG, PNG or PDF document",
        )
    if content_type and actual != content_type:
        # Declared JPEG but payload is a PDF etc. — trust the bytes.
        logger.info(
            "Receipt content-type mismatch (declared %s, actual %s); using bytes",
            content_type,
            actual,
        )
        content_type = actual

    textract = TextractService(settings)
    s3 = S3Service(settings)

    extraction = None
    if s3.enabled:
        try:
            ref = s3.upload_bytes(
                user_id=current_user.id,
                data=data,
                content_type=content_type,
                prefix="receipts",
            )
            extraction = textract.analyze_receipt(s3_key=ref["key"])
            logger.info(
                "Receipt archived to s3://%s/%s", settings.aws_s3_bucket, ref["key"]
            )
        except (S3Unavailable, TextractUnavailable) as exc:
            logger.warning("Receipt pipeline (S3 path) failed: %s", exc)
            extraction = None

    if extraction is None:  # no bucket configured → send bytes straight to Textract
        try:
            extraction = textract.analyze_receipt(data=data)
        except TextractUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Receipt OCR is not configured or currently unavailable. "
                "Configure AWS credentials (+ AWS_S3_BUCKET for archiving).",
            ) from exc

    # Normalise: prefer Bedrock when available, else the deterministic parser.
    raw_lines = extraction.raw_lines + [i["name"] for i in extraction.line_items]
    clean = BedrockService(settings).normalize_grocery_items(raw_lines)
    if clean:
        return [
            ReceiptItemOut(
                name=i["name"],
                quantity=i["quantity"],
                unit=i["unit"],
                category=i["category"],
                expiresAt=None,
                imageUrl=None,
                unitPrice=None,  # Bedrock path: prices come from Textract
                currency=None,
            )
            for i in clean
        ]
    return normalize_receipt_items(extraction.line_items, extraction.raw_lines)
