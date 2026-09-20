"""Unit canonicalisation / conversion and food-name matching helpers.

Everything is deterministic and pure — this module is shared by the risk
engine, the cook flow, shopping inventory checks and receipt OCR.
"""

from __future__ import annotations

import re

_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)

# Canonical spellings for units accepted by the API.
UNIT_ALIASES: dict[str, str] = {
    "g": "g", "gram": "g", "grams": "g", "gm": "g",
    "kg": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "millilitre": "ml", "milliliter": "ml",
    "l": "l", "lt": "l", "ltr": "l", "litre": "l", "liter": "l",
    "litres": "l", "liters": "l",
    "pc": "pcs", "pcs": "pcs", "piece": "pcs", "pieces": "pcs",
    "unit": "pcs", "units": "pcs", "nos": "pcs",
    "pack": "pack", "packs": "pack", "packet": "pack", "packets": "pack",
    "pkt": "pack", "box": "pack",
    "dozen": "dozen", "doz": "dozen",
    "bunch": "bunch", "bunches": "bunch",
    "loaf": "loaf", "tin": "pack", "can": "pack", "bottle": "pack",
}

# Base families for conversions.
MASS = {"g": 1.0, "kg": 1000.0}
VOLUME = {"ml": 0.001, "l": 1.0}
COUNT = {"pcs": 1.0, "pack": 1.0, "dozen": 12.0, "bunch": 1.0, "loaf": 1.0}

_FAMILIES = (MASS, VOLUME, COUNT)

# Category keyword map used when the caller doesn't supply a category.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Vegetables": (
        "spinach", "potato", "onion", "tomato", "carrot", "cucumber", "capsicum",
        "pepper", "broccoli", "cauliflower", "cabbage", "lettuce", "beans",
        "peas", "okra", "bhindi", "brinjal", "eggplant", "coriander", "spinach",
        "methi", "palak", "garlic", "ginger", "chilli", "pumpkin", "beetroot",
        "radish", "mushroom", "zucchini", "kale", "celery", "leek", "turnip",
    ),
    "Fruits": (
        "apple", "banana", "mango", "orange", "grape", "papaya", "pineapple",
        "watermelon", "melon", "strawberry", "blueberry", "berry", "kiwi",
        "pomegranate", "guava", "pear", "peach", "plum", "cherry", "lemon",
        "lime", "coconut", "avocado", "fig", "apricot",
    ),
    "Dairy": (
        "milk", "curd", "yogurt", "yoghurt", "dahi", "paneer", "cheese",
        "butter", "ghee", "cream", "buttermilk", "lassi", "khoya",
    ),
    "Meat & Fish": (
        "chicken", "mutton", "lamb", "fish", "prawn", "shrimp", "salmon",
        "beef", "pork", "egg", "eggs", "meat", "keema",
    ),
    "Bakery": (
        "bread", "bun", "croissant", "cake", "muffin", "bagel", "pav",
        "rusk", "naan", "roti wrap", "tortilla",
    ),
    "Pantry Staples": (
        "rice", "atta", "flour", "maida", "dal", "lentil", "sugar", "salt",
        "oil", "ghee", "spice", "masala", "turmeric", "cumin", "pasta",
        "noodle", "oats", "cereal", "quinoa", "poha", "suji", "besan",
        "rajma", "chana", "chickpea", "honey", "vinegar", "sauce", "jam",
        "peanut butter", "tea", "coffee",
    ),
    "Beverages": (
        "juice", "cola", "soda", "soft drink", "energy drink", "lassi",
    ),
    "Snacks": (
        "chips", "biscuit", "cookie", "namkeen", "chocolate", "candy",
        "popcorn", "nuts", "almond", "cashew", "raisin",
    ),
}


def canonical_unit(unit: str | None) -> str:
    """Map an arbitrary unit string to its canonical spelling."""
    if not unit:
        return "pcs"
    cleaned = unit.strip().lower().rstrip(".")
    return UNIT_ALIASES.get(cleaned, cleaned[:20] or "pcs")


def base_family(unit: str) -> dict[str, float] | None:
    """Return the conversion family a unit belongs to (or ``None``)."""
    unit = canonical_unit(unit)
    for family in _FAMILIES:
        if unit in family:
            return family
    return None


def to_base(quantity: float, unit: str) -> float:
    """Normalize a quantity to its family base (grams / litres / count)."""
    family = base_family(unit)
    if family is None:
        return quantity
    return quantity * family[canonical_unit(unit)]


def convert(quantity: float, from_unit: str, to_unit: str) -> float | None:
    """Convert between compatible units; ``None`` when incompatible."""
    f_from, f_to = base_family(from_unit), base_family(to_unit)
    if f_from is None or f_to is None or f_from is not f_to:
        return None
    base = quantity * f_from[canonical_unit(from_unit)]
    return base / f_to[canonical_unit(to_unit)]


def normalize_name(name: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation."""
    lowered = name.strip().lower()
    lowered = _PUNCTUATION_RE.sub(" ", lowered)
    return " ".join(lowered.split())


def _singular(word: str) -> str:
    """Deterministic English plural rules, applied to the FINAL word only.

    * ``tomatoes/potatoes/mangoes`` → ``-oes`` → strip 2
    * ``peaches/dishes/boxes`` → ``-ches/-shes/-xes/-ses`` → strip 2
    * ``berries`` → ``berry`` (``-ies`` → ``-y``)
    * ``onions/apples/eggs`` → plain ``-s`` stripped (``apples`` → apple,
      NOT ``appl`` — the plain-s rule fires last)
    * words ending in ``ss``/``us`` (hummus, cress) are left alone.
    """
    if word.endswith(("ss", "us")):
        return word
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("oes", "ches", "shes", "xes", "zes", "ses")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def canonical_food_key(name: str) -> str:
    """Canonical comparison key: normalized name with a singular last word."""
    words = normalize_name(name).split()
    if not words:
        return ""
    return " ".join([*words[:-1], _singular(words[-1])])


def names_match(a: str, b: str) -> bool:
    """Whole-name comparison on canonical keys.

    Handles tomato↔tomatoes, potato↔potatoes, onion↔onions, apple↔apples —
    while ``apple`` never matches ``apple juice`` (different canonical key).
    """
    return canonical_food_key(a) == canonical_food_key(b)


def categorize(name: str, fallback: str = "Other") -> str:
    """Best-effort grocery category from the item name."""
    lowered = normalize_name(name)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return fallback


def canonical_food_name(name: str) -> str:
    """Display name stored on ``Food`` rows: '  spinach ' → 'Spinach'."""
    return " ".join(name.strip().split()).capitalize()
