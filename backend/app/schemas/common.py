"""Shared serialization helpers.

The frontend contract expects ISO-8601 timestamps ending in ``Z`` and
quantities emitted as plain numbers (``250`` rather than ``250.0``).
"""

from datetime import UTC, datetime


def iso_z(value: datetime | None) -> str | None:
    """Serialize a (naive-UTC or aware) datetime as ``YYYY-MM-DDTHH:MM:SS.ssZ``."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def tidy_quantity(value: float) -> float | int:
    """Emit whole quantities as ints so JSON shows ``250`` not ``250.0``."""
    return int(value) if float(value).is_integer() else round(value, 3)
