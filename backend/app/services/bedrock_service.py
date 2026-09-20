"""Amazon Bedrock integration (recipe + grocery-normalisation AI).

Design notes
────────────
* Only CURATED, structured context is sent to the model (urgent items with
  quantities/risk + available item names) — never the raw database.
* Output is strictly validated with Pydantic before use.
* Every failure (missing credentials, throttling, malformed JSON) raises
  ``BedrockUnavailable`` so callers fall back to the deterministic
  generator — the API keeps working without AWS configured.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.recipe import AIRecipe, AIRecipeList

logger = logging.getLogger(__name__)


class BedrockUnavailable(Exception):
    """Raised for any Bedrock failure; callers must have a fallback."""


_RECIPE_SYSTEM_PROMPT = """You are SmartPantry's food-rescue chef.
You help households cook food before it spoils.

You receive JSON with:
  "urgent_items"    — ingredients at risk of being wasted (name, quantity, unit, risk, days_until_expiry)
  "available_items" — other stocked ingredient names the user can combine with them.

Return ONLY a JSON object (no markdown, no commentary):
{"recipes": [
  {
    "name": "short appetising dish name",
    "ingredients": [{"name": "...", "quantity": 250.0, "unit": "g"}],
    "reasoning": "one or two sentences explaining which at-risk ingredients this rescues and why",
    "instructions": ["step 1", "step 2", "step 3", "step 4"]
  }
]}

Rules:
- Prioritise the highest-risk urgent ingredients in every recipe; each recipe must use >=1 urgent item.
- Never request more of an ingredient than the listed quantity.
- Available/staple items may be added in realistic home-kitchen amounts.
- 4-8 simple instruction steps per recipe. Cuisines may vary (Indian, Italian, Asian...).
- Quantities must be positive numbers; units from: g, kg, ml, l, pcs, pack."""


class BedrockService:
    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()
        self._client = None
        self._disabled_reason: str | None = None

    # ── availability ─────────────────────────────────────────────────
    @property
    def enabled(self) -> bool:
        return bool(self._settings.bedrock_model_id) and self._disabled_reason is None

    @property
    def disabled_reason(self) -> str | None:
        if not self._settings.bedrock_model_id:
            return "BEDROCK_MODEL_ID is not configured"
        return self._disabled_reason

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:  # boto3 imported lazily so tests don't need AWS at all
            import boto3
            from botocore.config import Config
            from botocore.exceptions import NoCredentialsError

            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self._settings.aws_region,
                aws_access_key_id=self._settings.aws_access_key_id,
                aws_secret_access_key=self._settings.aws_secret_access_key,
                config=Config(
                    connect_timeout=5, read_timeout=45, retries={"max_attempts": 1}
                ),
            )
        except NoCredentialsError as exc:
            self._disabled_reason = "AWS credentials not found"
            raise BedrockUnavailable(self._disabled_reason) from exc
        except Exception as exc:  # pragma: no cover - environment specific
            self._disabled_reason = f"Bedrock client init failed: {exc!r}"
            raise BedrockUnavailable(self._disabled_reason) from exc
        return self._client

    # ── low-level ────────────────────────────────────────────────────
    def _converse(self, *, system: str, user_payload: dict[str, Any],
                  max_tokens: int = 2000, temperature: float = 0.4) -> str:
        """Call the Bedrock Converse API (works across model families)."""
        try:
            from botocore.exceptions import BotoCoreError, ClientError

            client = self._get_client()
            response = client.converse(
                modelId=self._settings.bedrock_model_id,
                system=[{"text": system}],
                messages=[
                    {"role": "user", "content": [{"text": json.dumps(user_payload)}]}
                ],
                inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
            )
            return response["output"]["message"]["content"][0]["text"]
        except BedrockUnavailable:
            raise
        except (BotoCoreError, ClientError, KeyError, IndexError) as exc:
            logger.warning("Bedrock converse failed: %r", exc)
            raise BedrockUnavailable(f"Bedrock call failed: {exc!r}") from exc

    @staticmethod
    def _extract_json(text: str) -> Any:
        """Pull the first JSON object/array out of a model response."""
        text = text.strip()
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"[\[{].*[\]}]", text, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise

    # ── 1. food-rescue recipes ───────────────────────────────────────
    def generate_recipes(
        self,
        *,
        urgent_items: list[dict[str, Any]],
        available_items: list[str],
        max_recipes: int = 3,
    ) -> list[AIRecipe]:
        if not self.enabled:
            raise BedrockUnavailable(self.disabled_reason or "Bedrock disabled")
        payload = {
            "urgent_items": urgent_items,
            "available_items": available_items,
            "max_recipes": max_recipes,
        }
        raw = self._converse(system=_RECIPE_SYSTEM_PROMPT, user_payload=payload)
        try:
            parsed = self._extract_json(raw)
            if isinstance(parsed, list):  # some models return a bare array
                parsed = {"recipes": parsed}
            validated = AIRecipeList.model_validate(parsed)
            return validated.recipes[:max_recipes]
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Bedrock returned unusable recipe JSON: %r", exc)
            raise BedrockUnavailable("Bedrock output failed validation") from exc

    # ── 2. grocery normalisation (receipt OCR post-processing) ──────
    def normalize_grocery_items(
        self, raw_lines: list[str], max_items: int = 30
    ) -> list[dict[str, Any]]:
        """Turn messy OCR lines into {name, quantity, unit, category} dicts.

        Returns ``[]`` (and lets callers fall back to the local parser)
        whenever Bedrock is unavailable or output is unusable.
        """
        if not self.enabled or not raw_lines:
            return []
        system = (
            "You normalize grocery receipt lines. Return ONLY JSON: "
            '{"items":[{"name":"clean product name","quantity":1.0,'
            '"unit":"g|kg|ml|l|pcs|pack","category":"Vegetables|Fruits|Dairy|'
            'Meat & Fish|Bakery|Pantry Staples|Beverages|Snacks|Frozen|Other"}]}. '
            "Skip totals, taxes, payments, loyalty lines. Merge duplicates. "
            "Infer sensible package quantities (e.g. 'MILK 1L' → 1 l)."
        )
        try:
            raw = self._converse(
                system=system, user_payload={"lines": raw_lines[:80]}, max_tokens=1500,
            )
            parsed = self._extract_json(raw)
            items = parsed.get("items", parsed if isinstance(parsed, list) else [])
            clean: list[dict[str, Any]] = []
            for item in items[:max_items]:
                try:
                    name = str(item["name"]).strip()
                    if not name:
                        continue
                    clean.append(
                        {
                            "name": name,
                            "quantity": float(item.get("quantity") or 1),
                            "unit": str(item.get("unit") or "pcs"),
                            "category": str(item.get("category") or "Other"),
                        }
                    )
                except (KeyError, TypeError, ValueError):
                    continue
            return clean
        except BedrockUnavailable:
            return []
