"""Local grocery-line normaliser — deterministic fallback used when
Bedrock normalisation is unavailable.

Input: Textract line items like::

    {"name": "AMUL MILK 1L", "quantity": "2", "price": "130.00"}

Output: clean ``{"name": "Amul Milk", "quantity": 2, "unit": "l",
"category": "Dairy"}`` dicts, capped and de-duplicated.
"""

from __future__ import annotations

import re

from app.schemas.receipt import ReceiptItemOut
from app.services.units import canonical_unit, categorize

# Lines that are never grocery items.
_SKIP_WORDS = (
    "total", "subtotal", "sub total", "cgst", "sgst", "igst", "gst", "tax",
    "cash", "change", "tender", "balance", "visa", "mastercard", "credit",
    "debit", "upi", "card", "round off", "rounding", "discount", "savings",
    "you saved", "bill no", "invoice", "counter", "cashier", "thank",
    "welcome", "phone", "mobile", "customer", "loyalty", "points",
)

_QTY_UNIT_RE = re.compile(
    r"(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|gm|ml|l|ltr|litre|liter|pcs|pc|pack|pkt|nos)\b",
    re.IGNORECASE,
)
_MULTIPLIER_RE = re.compile(r"^(?P<qty>\d+)\s*[x×]\s+", re.IGNORECASE)
_TRAILING_JUNK_RE = re.compile(r"[\s:;*\-.,#|/\\]+$")
_PRICE_TOKEN_RE = re.compile(r"\b\d+\.\d{2}\b")
_NUM_PRICE_RE = re.compile(r"[^\d.,]")


def _parse_price(raw: str | None, quantity: float) -> float | None:
    """Textract's PRICE field is a LINE total — derive per-unit price.

    Only used when a genuine numeric price was read; anything ambiguous
    stays ``None`` (never estimated)."""
    if not raw:
        return None
    cleaned = _NUM_PRICE_RE.sub("", raw).replace(",", "")
    try:
        total = float(cleaned)
    except ValueError:
        return None
    if total <= 0:
        return None
    if quantity and quantity > 1:
        unit = total / quantity
        return round(unit, 2) if unit > 0 else None
    return round(total, 2)


def _looks_skip(line: str) -> bool:
    lowered = line.lower()
    return any(word in lowered for word in _SKIP_WORDS)


def parse_line(name: str, quantity_field: str | None) -> dict | None:
    """Parse one OCR line → {name, quantity, unit} or ``None`` to skip."""
    if not name or _looks_skip(name) or len(name) < 2:
        return None

    count = 1.0  # how many purchasable units (from "2 X …" or QUANTITY col)
    m = _MULTIPLIER_RE.match(name)
    if m:
        count *= float(m.group("qty"))
        name = name[m.end():]
    if quantity_field:
        try:
            field_qty = float(str(quantity_field).replace(",", "."))
            if field_qty > 0:
                count *= field_qty
        except ValueError:
            pass

    qty, unit = 1.0, "pcs"
    match = _QTY_UNIT_RE.search(name)
    if match and float(match.group("qty").replace(",", ".")) > 0:
        # Embedded pack size (MILK 1L) — the COUNT is the true quantity.
        embedded = float(match.group("qty").replace(",", "."))
        unit = canonical_unit(match.group("unit"))
        qty = embedded * count
        name = (name[: match.start()] + name[match.end():]).strip()
    else:
        qty = count

    clean = _TRAILING_JUNK_RE.sub("", _PRICE_TOKEN_RE.sub("", name)).strip(" .-_")
    # Collapse whitespace, drop obvious non-words, title-case SHOUTING.
    clean = " ".join(clean.split())
    if len(clean) < 2 or not any(ch.isalpha() for ch in clean):
        return None
    if clean.isupper() and len(clean) > 3:
        clean = clean.title()

    return {"name": clean[:160], "quantity": qty, "unit": unit}


def normalize_receipt_items(
    line_items: list[dict], raw_lines: list[str], max_items: int = 30
) -> list[ReceiptItemOut]:
    """Textract line items (+ raw lines as a fallback) → receipt DTOs."""
    parsed: list[dict] = []
    for item in line_items:
        result = parse_line(item.get("name", ""), item.get("quantity"))
        if result:
            result["unit_price"] = _parse_price(item.get("price"), result["quantity"])
            parsed.append(result)
    if not parsed:  # crude text-only fallback: one item per plausible line
        for line in raw_lines:
            result = parse_line(line, None)
            if result:
                result["unit_price"] = None
                parsed.append(result)

    out: list[ReceiptItemOut] = []
    seen: set[str] = set()
    for item in parsed[: max_items * 2]:
        key = item["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            ReceiptItemOut(
                name=item["name"],
                quantity=item["quantity"],
                unit=item["unit"],
                category=categorize(item["name"]),
                expiresAt=None,
                imageUrl=None,
                unitPrice=item.get("unit_price"),
                currency=None,
            )
        )
        if len(out) >= max_items:
            break
    return out
