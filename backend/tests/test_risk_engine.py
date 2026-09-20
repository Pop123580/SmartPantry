"""Pure risk-engine unit tests: safe / expiring / high-risk / running-low
plus the deterministic score formula's edge cases."""

from datetime import UTC, datetime, timedelta

from app.services.risk_engine import (
    Risk,
    Status,
    assess,
    default_shelf_life_days,
    estimate_perishability,
    expiring_soon_window,
)
from app.services.units import convert, names_match, to_base

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
NAIVE_NOW = NOW.replace(tzinfo=None)


def _expiry(days: float) -> datetime:
    return NAIVE_NOW + timedelta(days=days)


def test_spinach_spec_example():
    """Spinach, 250 g, expires tomorrow, high perishability →
    status expiring_soon, risk high (the spec's exact example)."""
    result = assess(
        quantity=250,
        unit="g",
        perishability_score=10,
        expires_at=_expiry(1),
        now=NAIVE_NOW,
    )
    assert result.status == Status.EXPIRING_SOON
    assert result.risk == Risk.HIGH


def test_safe_staple():
    result = assess(
        quantity=5,
        unit="kg",
        perishability_score=1,
        expires_at=_expiry(365),
        now=NAIVE_NOW,
    )
    assert result.status == Status.SAFE
    assert result.risk == Risk.LOW


def test_expired_item_is_max_risk():
    result = assess(
        quantity=2, unit="kg", perishability_score=1,
        expires_at=_expiry(-2), now=NAIVE_NOW,
    )
    assert result.status == Status.EXPIRING_SOON
    assert result.risk == Risk.HIGH
    assert result.risk_score == 1.0


def test_running_low():
    result = assess(
        quantity=1, unit="pcs", perishability_score=2,
        expires_at=_expiry(200), now=NAIVE_NOW,
    )
    assert result.status == Status.RUNNING_LOW

    result_g = assess(
        quantity=100, unit="g", perishability_score=1,
        expires_at=_expiry(200), now=NAIVE_NOW,
    )
    assert result_g.status == Status.RUNNING_LOW

    # comfortable stock stays safe
    result_ok = assess(
        quantity=2, unit="kg", perishability_score=1,
        expires_at=_expiry(200), now=NAIVE_NOW,
    )
    assert result_ok.status == Status.SAFE


def test_expiring_takes_precedence_over_running_low():
    result = assess(
        quantity=50, unit="g", perishability_score=8,  # tiny stock AND expiring
        expires_at=_expiry(1), now=NAIVE_NOW,
    )
    assert result.status == Status.EXPIRING_SOON


def test_consumption_history_reduces_risk():
    """Regularly-eaten food is less likely to be wasted (same item, same
    expiry — one with a strong consumption history)."""
    heavy_use = assess(
        quantity=500, unit="g", perishability_score=8,
        expires_at=_expiry(5), consumption_events_30d=10, now=NAIVE_NOW,
    )
    no_use = assess(
        quantity=500, unit="g", perishability_score=8,
        expires_at=_expiry(5), consumption_events_30d=0, now=NAIVE_NOW,
    )
    assert no_use.risk == Risk.MEDIUM  # 0.6*(2/7) + 0.4*(7/9) ≈ 0.48
    assert heavy_use.risk == Risk.LOW   # ~0.24 after the 50 % discount


def test_high_perishability_no_expiry_is_medium_not_urgent():
    result = assess(
        quantity=500, unit="g", perishability_score=10,
        expires_at=None, now=NAIVE_NOW,
    )
    assert result.status == Status.SAFE
    assert result.risk == Risk.MEDIUM


# ── §9 edge cases ────────────────────────────────────────────────────


def test_expires_today_is_expiring_soon():
    result = assess(
        quantity=400, unit="g", perishability_score=5,
        expires_at=_expiry(0), now=NAIVE_NOW,
    )
    assert result.days_until_expiry == 0
    assert result.status == Status.EXPIRING_SOON
    assert result.risk in (Risk.MEDIUM, Risk.HIGH)


def test_expires_tomorrow_low_perishability():
    """Rice expiring tomorrow: yes it's urgent by date, but perishability
    1 keeps the window at 1 day — tomorrow still counts."""
    result = assess(
        quantity=2, unit="kg", perishability_score=1,
        expires_at=_expiry(1), now=NAIVE_NOW,
    )
    assert result.status == Status.EXPIRING_SOON
    # date-driven urgency dominates → high risk even for a staple
    assert result.risk == Risk.HIGH


def test_no_expiry_high_quantity_is_safe():
    result = assess(
        quantity=10, unit="kg", perishability_score=1,
        expires_at=None, now=NAIVE_NOW,
    )
    assert result.status == Status.SAFE
    assert result.risk == Risk.LOW
    assert result.days_until_expiry is None


def test_no_expiry_high_perishability_large_stock():
    result = assess(
        quantity=5, unit="kg", perishability_score=10,
        expires_at=None, now=NAIVE_NOW,
    )
    assert result.status == Status.SAFE
    assert result.risk == Risk.MEDIUM  # perish 10 → 0.4·1.0 = 0.40


def test_zero_quantity_is_running_low_not_crash():
    result = assess(
        quantity=0, unit="g", perishability_score=5,
        expires_at=None, now=NAIVE_NOW,
    )
    assert result.status == Status.RUNNING_LOW


def test_zero_quantity_expiring_item_prioritizes_expiry():
    result = assess(
        quantity=0, unit="g", perishability_score=8,
        expires_at=_expiry(1), now=NAIVE_NOW,
    )
    assert result.status == Status.EXPIRING_SOON


def test_invalid_negative_quantity_clamped_to_zero():
    result = assess(
        quantity=-50, unit="g", perishability_score=1,
        expires_at=None, now=NAIVE_NOW,
    )
    assert result.status == Status.RUNNING_LOW  # treated as 0, not a crash


def test_non_perishable_staple_all_states():
    far = assess(quantity=1, unit="kg", perishability_score=1,
                 expires_at=_expiry(400), now=NAIVE_NOW)
    assert (far.status, far.risk) == (Status.SAFE, Risk.LOW)
    low = assess(quantity=50, unit="g", perishability_score=1,
                 expires_at=_expiry(400), now=NAIVE_NOW)
    assert low.status == Status.RUNNING_LOW


def test_recently_consumed_item_scores_lower():
    """Consumption history lowers the risk of items NOT yet inside the
    expiring window (the household demonstrably eats them before waste);
    inside the window, the expiry date dominates deterministically."""
    # outside the window (paneer, perish 8 → window 4 d): history wins
    eaten = assess(quantity=400, unit="g", perishability_score=8,
                   expires_at=_expiry(5), consumption_events_30d=10,
                   now=NAIVE_NOW)
    ignored = assess(quantity=400, unit="g", perishability_score=8,
                     expires_at=_expiry(5), consumption_events_30d=0,
                     now=NAIVE_NOW)
    assert eaten.risk_score < ignored.risk_score
    assert eaten.risk == Risk.LOW and ignored.risk == Risk.MEDIUM

    # inside the window the date-driven floor pin applies to BOTH —
    # spoiling food is urgent regardless of household habits
    eaten_urgent = assess(quantity=250, unit="g", perishability_score=10,
                          expires_at=_expiry(3), consumption_events_30d=10,
                          now=NAIVE_NOW)
    ignored_urgent = assess(quantity=250, unit="g", perishability_score=10,
                            expires_at=_expiry(3), consumption_events_30d=0,
                            now=NAIVE_NOW)
    assert eaten_urgent.status == ignored_urgent.status == Status.EXPIRING_SOON
    assert eaten_urgent.risk == ignored_urgent.risk == Risk.HIGH


# ── helpers ──────────────────────────────────────────────────────────


def test_window_scales_with_perishability():
    assert expiring_soon_window(1) == 1
    assert expiring_soon_window(5) == 2
    assert expiring_soon_window(7) == 3
    assert expiring_soon_window(10) == 4


def test_units_convert():
    assert to_base(1.5, "kg") == 1500
    assert to_base(500, "ml") == 0.5
    assert convert(500, "g", "kg") == 0.5
    assert convert(1, "l", "ml") == 1000
    assert convert(1, "g", "l") is None  # incompatible families


def test_name_matching_plural_insensitive():
    assert names_match("Tomatoes", "tomato")
    assert names_match("Brown Rice", "  brown   rice ")
    assert not names_match("Milk", "Milk Powder")


def test_food_matching_spec_variations():
    """tomato/tomatoes, potato/potatoes, onion/onions, apple/apples."""
    assert names_match("tomato", "tomatoes")
    assert names_match("potato", "potatoes")
    assert names_match("Onion", "ONIONS  ")
    assert names_match("apple", "Apples")
    assert names_match("strawberry", "strawberries")
    assert names_match("Egg", "eggs")
    # punctuation / whitespace noise tolerated
    assert names_match("green-apples", "Green Apples")
    assert names_match("  Tomato, ", "tomatoes")
    # words ending in s that aren't plurals stay put
    assert names_match("hummus", "Hummus")
    # NO false positives across different names
    assert not names_match("apple", "apple juice")
    assert not names_match("tomato", "potato")
    assert not names_match("milk", "chocolate milk")
    assert not names_match("rice", "rice flour")


def test_perishability_estimates():
    assert estimate_perishability("Fresh Spinach") == 10
    assert estimate_perishability("Curd") == 8
    assert estimate_perishability("Basmati Rice", "Pantry Staples") == 1
    assert 1 <= estimate_perishability("Mystery Item", None) <= 10
    assert default_shelf_life_days(10) < default_shelf_life_days(1)
