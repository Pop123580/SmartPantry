"""Deterministic pantry risk engine.

PURE LOGIC — no database, no AI. The LLM never decides whether food is
at risk; it only *narrates* recipes around decisions made here.

Inputs                          Outputs
─────────────────────────────   ──────────────────────────────────────
days until expiry         ┐
food perishability (1-10)  ├─→  risk   : "low" | "medium" | "high"
remaining quantity         │
consumption history       ┘     status : "safe" | "expiring_soon" | "running_low"

Worked example (the spec's example):
    Spinach, 250 g, expires tomorrow, perishability 10
      → status = expiring_soon, risk = high
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.services.units import base_family, to_base

# ── Tunables (documented, deterministic) ─────────────────────────────
#: An expiry further out than this contributes zero waste risk.
FAR_EXPIRY_DAYS = 7.0
#: Stock at or below these base-unit levels is "running low".
LOW_STOCK_THRESHOLD = {"g": 150.0, "l": 0.3, "count": 1.0}
#: Consumption-log events in 30 days that count as "regularly eaten".
REGULAR_CONSUMPTION_EVENTS = 10
#: risk_score >= 0.66 → high; >= 0.40 → medium; else low.
HIGH_RISK_CUTOFF = 0.66
MEDIUM_RISK_CUTOFF = 0.40


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Status(StrEnum):
    SAFE = "safe"
    EXPIRING_SOON = "expiring_soon"
    RUNNING_LOW = "running_low"


@dataclass(frozen=True)
class RiskAssessment:
    status: Status
    risk: Risk
    days_until_expiry: float | None
    risk_score: float
    expiry_score: float
    perishability_score: float


def expiring_soon_window(perishability_score: int) -> int:
    """How many days before expiry an item is flagged ``expiring_soon``.

    Highly perishable food spoils faster, so it is flagged earlier:
    score 1-2 → 1 day, 3-5 → 2 days, 6-7 → 3 days, 8-10 → 4 days.
    """
    score = min(max(int(perishability_score), 1), 10)
    return max(1, math.ceil(score / 2.5))


def days_until(expiry: datetime | None, now: datetime) -> float | None:
    """Fractional days until expiry (negative when already expired).

    Both datetimes must be naive-UTC (the project's storage convention) or
    both tz-aware; mismatched awareness is normalized to naive-UTC.
    """
    if expiry is None:
        return None
    if expiry.tzinfo is not None and now.tzinfo is None:
        from datetime import UTC

        expiry = expiry.astimezone(UTC).replace(tzinfo=None)
    elif now.tzinfo is not None and expiry.tzinfo is None:
        from datetime import UTC

        now = now.astimezone(UTC).replace(tzinfo=None)
    return (expiry - now).total_seconds() / 86_400


def expiry_score(days: float | None) -> float:
    """1.0 expired → 0.0 when ``FAR_EXPIRY_DAYS`` or more remain."""
    if days is None:
        return 0.0
    if days < 0:
        return 1.0
    return max(0.0, min(1.0, (FAR_EXPIRY_DAYS - days) / FAR_EXPIRY_DAYS))


def _perishability_norm(perishability_score: int) -> float:
    score = min(max(int(perishability_score), 1), 10)
    return (score - 1) / 9.0


def low_stock_threshold(unit: str) -> float:
    family = base_family(unit)
    if family is None:
        return LOW_STOCK_THRESHOLD["count"]
    if family.get("g"):
        return LOW_STOCK_THRESHOLD["g"]
    if family.get("l") is not None and "ml" in family:
        return LOW_STOCK_THRESHOLD["l"]
    return LOW_STOCK_THRESHOLD["count"]


def assess(
    *,
    quantity: float,
    unit: str,
    perishability_score: int,
    expires_at: datetime | None,
    consumption_events_30d: int = 0,
    now: datetime,
) -> RiskAssessment:
    """Assess one pantry item. All inputs are explicit → fully testable.

    Risk score
    ----------
    ``0.6 * expiry_score + 0.4 * perishability_norm``
    discounted by up to 50 % when the household demonstrably eats this
    item (consumption history), because regularly-used food rarely goes
    to waste. Expired/expiring items are pinned to at least 1.0 / 0.75.

    Defensive: invalid (negative) quantities are clamped to 0 → the item
    reports as running_low rather than crashing the pipeline.
    """
    quantity = max(0.0, float(quantity))
    days = days_until(expires_at, now)
    exp_score = expiry_score(days)
    perish = _perishability_norm(perishability_score)
    history = min(consumption_events_30d, REGULAR_CONSUMPTION_EVENTS) / float(
        REGULAR_CONSUMPTION_EVENTS
    )

    score = (0.6 * exp_score + 0.4 * perish) * (1.0 - 0.5 * history)

    window = expiring_soon_window(perishability_score)
    is_expired = days is not None and days < 0
    is_expiring_soon = days is not None and days <= window
    if is_expired:
        score = 1.0
    elif is_expiring_soon:
        score = max(score, 0.75)

    if score >= HIGH_RISK_CUTOFF:
        risk = Risk.HIGH
    elif score >= MEDIUM_RISK_CUTOFF:
        risk = Risk.MEDIUM
    else:
        risk = Risk.LOW

    # Status precedence: expiry first (rescue the food!), then stock level.
    if is_expired or is_expiring_soon:
        status = Status.EXPIRING_SOON
    elif to_base(quantity, unit) <= low_stock_threshold(unit):
        status = Status.RUNNING_LOW
    else:
        status = Status.SAFE

    return RiskAssessment(
        status=status,
        risk=risk,
        days_until_expiry=days,
        risk_score=round(score, 4),
        expiry_score=round(exp_score, 4),
        perishability_score=round(perish, 4),
    )


# ── Catalogue heuristics (used when foods are first created) ─────────

_HIGH_PERISH = (
    "spinach", "palak", "lettuce", "coriander", "cilantro", "mint", "kale",
    "methi", "strawberry", "raspberry", "fish", "prawn", "shrimp", "mutton",
    "chicken", "keema", "mince",
)
_MEDIUM_HIGH_PERISH = (
    "milk", "curd", "yogurt", "yoghurt", "dahi", "paneer", "cream",
    "buttermilk", "banana", "tomato", "cucumber", "mushroom", "berry",
    "berries", "papaya", "bread", "pav", "bun",
)
_MEDIUM_PERISH = (
    "egg", "cheese", "butter", "carrot", "capsicum", "broccoli", "beans",
    "cauliflower", "cabbage", "apple", "orange", "mango", "grape", "guava",
)
_LOW_PERISH = (
    "onion", "potato", "garlic", "ginger", "lemon", "pumpkin", "beetroot",
)


def estimate_perishability(name: str, category: str | None = None) -> int:
    """1-10 perishability guess for a new ``Food`` row."""
    lowered = " ".join(name.lower().split())
    if any(word in lowered for word in _HIGH_PERISH):
        return 10
    if any(word in lowered for word in _MEDIUM_HIGH_PERISH):
        return 8
    if any(word in lowered for word in _MEDIUM_PERISH):
        return 5
    if any(word in lowered for word in _LOW_PERISH):
        return 3
    category_defaults = {
        "Vegetables": 7, "Fruits": 7, "Dairy": 8, "Meat & Fish": 9,
        "Bakery": 6, "Frozen": 3, "Beverages": 2, "Snacks": 2,
        "Pantry Staples": 1, "Household": 1,
    }
    return category_defaults.get(category or "", 5)


def default_shelf_life_days(perishability_score: int) -> int:
    """Default expiry estimate used when checkout adds an item whose shelf
    life the user hasn't entered: leafy greens ~3 days → staples ~1 year."""
    table = {10: 3, 9: 4, 8: 7, 7: 10, 6: 6, 5: 14, 4: 21, 3: 35, 2: 90, 1: 365}
    score = min(max(int(perishability_score), 1), 10)
    return table[score]
