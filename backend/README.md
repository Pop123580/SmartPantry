# SmartPantry — FastAPI Backend

Backend for the existing SmartPantry frontend: JWT auth, pantry CRUD with a
deterministic food-risk engine, Bedrock recipe generation, inventory-aware
shopping with atomic checkout, purchase history with real prices, and
Textract receipt OCR.

```
React + Vite (5173)
      │  VITE_API_BASE_URL=http://localhost:8000
      ▼
FastAPI (8000) ──┬─ Authentication (JWT Bearer, Argon2 hashing)
                 ├─ Pantry CRUD + deterministic Risk Engine
                 ├─ Recipes (Amazon Bedrock → validated AI output; deterministic fallback)
                 ├─ Cook flow (transactional, FEFO, never negative stock)
                 ├─ Shopping (inventory-aware) + atomic Checkout
                 ├─ Purchase history (Purchase + PurchaseItem, real prices)
                 └─ Receipt OCR (S3 → Textract → normalize → confirm → pantry)
      ▼
PostgreSQL (RDS in prod)      AWS: Bedrock · Textract · S3
```

Interactive docs: **`/docs`** and **`/openapi.json`** · Health: **`/api/health`**

---

## 1 · Local setup

```bash
cd backend

# 1-2. virtual environment
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. dependencies
pip install -r requirements.txt

# 4. environment
cp .env.example .env

# 5. PostgreSQL — one of:
docker compose up -d db            # Docker (recommended for dev)
createdb smartpantry               # local Postgres
# or paste an Amazon RDS URL into DATABASE_URL

# 6. JWT secret — REQUIRED, no default is provided
openssl rand -hex 32               # → set as JWT_SECRET_KEY in .env

# 7. migrations
alembic upgrade head

# 8. run
uvicorn app.main:app --reload --port 8000

# 9. open Swagger
open http://localhost:8000/docs
```

End-to-end confidence check against the running API:

```bash
python scripts/demo_flow.py        # full story incl. purchases + analytics
pytest -q                          # complete test suite (SQLite, no AWS)
python -m compileall -q app tests  # syntax check
```

## 2 · Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `ENVIRONMENT` | — | `development / test / staging / production` |
| `DATABASE_URL` | ✅ | e.g. `postgresql+psycopg://user:pass@host:5432/smartpantry` |
| `JWT_SECRET_KEY` | ✅ | HS256 signing secret — **required, no default** (see §3) |
| `JWT_ALGORITHM` | — | default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | default `10080` (7 days) |
| `FRONTEND_URL` | ✅ | CORS origin |
| `AWS_REGION` | AWS | e.g. `ap-south-1` (Bedrock/Textract/S3 region) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS | IAM — or omit & use the standard AWS credential chain |
| `AWS_S3_BUCKET` | AWS | receipt archive bucket |
| `BEDROCK_MODEL_ID` | AWS | any Bedrock **Converse**-capable model |
| `MAX_UPLOAD_SIZE_MB` | — | receipt cap, default `5` |
| `DEFAULT_CURRENCY` | — | ISO code printed with money values, default `INR` |

Never commit `.env`. `.env.example` contains placeholders only.

## 3 · Authentication & JWT security

* `POST /api/auth/register` → 201 + `{access_token, token_type, user}` (arguably
  also a 409 for duplicate email), `POST /api/auth/login`, `GET /api/auth/me`,
  `POST /api/auth/logout`.
* Passwords hashed with **Argon2** (bcrypt verifier retained for legacy hashes).
* Every user-scoped route resolves the user **only from the Bearer JWT** — a
  client-supplied `user_id` is never accepted.
* **Secret handling:** `JWT_SECRET_KEY` must come from the environment. There is
  no hardcoded fallback. Missing/blank → startup fails with a clear message;
  `staging`/`production` additionally require ≥ 32 characters. The secret is
  stored as `SecretStr` so it can never appear in reprs, model dumps, logs,
  API responses or Swagger examples. Legacy `JWT_SECRET` still works as a
  deprecated env alias for existing local setups.

### Logout semantics (known limitation)

JWTs are stateless — **logout does not revoke the token server-side.** The
client deletes its stored token; the endpoint is a lifecycle hook only
(response includes `"revokedOnServer": false` to be explicit). There is no
Redis blacklist in the MVP by design. Emergency invalidation of every session:
rotate `JWT_SECRET_KEY` and redeploy (all existing tokens fail validation).
Short token lifetime + TLS is the primary mitigation until refresh-token
rotation is added.

## 4 · Risk engine (`app/services/risk_engine.py`)

Deterministic — never an LLM. Fully unit-tested including edge cases
(expired, today, tomorrow, no-expiry, zero/negative quantity, perishability
extremes, consumption-history discount).

```
risk_score = (0.6·expiry_score + 0.4·perishability) · (1 − 0.5·history)
risk    ≥ 0.66 high · ≥ 0.40 medium · else low
status  expiry within perishability-scaled window → expiring_soon
        stock ≤ threshold (150 g / 0.3 l / 1 pc)   → running_low
        otherwise                                  → safe
```

## 5 · Recipes & cooking

* `GET /api/recipes/recommended` — pantry risk snapshot → urgent items to
  **Amazon Bedrock** (only names/quantities/risk, never raw user rows) →
  Pydantic-validated recipes. Bedrock missing/failing → **deterministic
  fallback generator** (the Food Rescue page always works).
* `POST /api/recipes/{id}/cook` — one transaction: match ingredients
  (plural-insensitive), convert units (g↔kg, ml↔l), FEFO across batches,
  subtract (never below zero), write consumption logs, recalc risk.
  Insufficient stock → **409 with per-ingredient shortfall details**; nothing
  changes.

## 6 · Shopping, checkout & purchase history

* `POST /api/shopping` accepts optional `unitPrice`/`currency` — real prices
  the user happens to know. No price → fields stay `null` everywhere.
* `POST /api/shopping/checkout` is **atomic**: validate → `Purchase` →
  `PurchaseItem`s (prices only where real) → pantry upsert (stock +
  `purchase_price` + `purchase_id`) → clear list. Any failure rolls back the
  entire transaction — never a partial purchase.
* `GET /api/purchases` / `GET /api/purchases/{id}` — history with line items.
* DB-level `CHECK quantity >= 0` on pantry stock backs the app logic.

## 7 · Analytics — honest money only

`GET /api/analytics/summary` returns the legacy fields the frontend uses
plus richer ones. Monetary values come ONLY from recorded prices:

| Field | Semantics |
|---|---|
| `atRiskKnownValue` | Σ remaining qty × recorded `purchase_price` over at-risk items · **`null` = unknown** |
| `atRiskValueUnavailableCount` | at-risk items without price → UI shows “N items at risk — value unavailable” |
| `totalPurchaseValue` | Σ `Purchase.total_amount` where priced |
| `knownValueSaved` | consumed qty × real price of that stock · null if none |
| `wasteEstimatedValue` | user-entered values or derived from recorded item price · never guessed |

Plus `recentConsumption`, `recentWaste`, `recentPurchases` feeds. Nothing is
fabricated; without prices you get counts, not rupees.

## 8 · Receipt pipeline

`POST /api/receipt/upload` (multipart). JPEG / PNG / PDF only, ≤
`MAX_UPLOAD_SIZE_MB` (default 5 MB). Validation is content-based (magic
bytes), not filename/declared-type. Flow: S3 archive (if bucket configured;
else raw bytes) → Textract `AnalyzeExpense` → normalize (Bedrock if
available, deterministic parser otherwise — line prices → per-unit prices
where readable) → **`CreatePantryItemDTO[]` returned for user confirmation —
nothing is auto-inserted into the pantry.** Without AWS credentials the
endpoint answers a clear `503`.

## 9 · Food matching

Deterministic canonical keys: lowercase, punctuation/whitespace stripped,
last-word singularization (`tomato↔tomatoes`, `potato↔potatoes`,
`strawberry↔strawberries`, `hummus` untouched). Whole-name comparison only —
`apple` never matches `apple juice`.

## 10 · Database & migrations

PostgreSQL-targeted SQLAlchemy 2 models (tests may use SQLite — no
SQLite-specific behavior is relied upon in app code). `sa.Uuid`, FKs with
explicit `ON DELETE` behavior, money as `Numeric(12,2)`, naive-UTC
timestamps serialized with `Z`. Migrations are append-only:

| Migration | Contents |
|---|---|
| `0001_initial` | users, foods, pantry_items, recipes, recipe_ingredients, shopping_items, consumption_logs, waste_logs, purchases |
| `0002_purchase_history` | `purchase_items` table; `purchases.purchased_at` rename + `currency`/`source`; pantry price/`purchase_id` + quantity CHECKs; consumption/waste `food_name` snapshots |

Fresh DB: `alembic upgrade head`. Downgrades verified. Old migrations are
never edited destructively — new schema changes always arrive as new files.

## 11 · API surface

| Method & path | Auth | Notes |
|---|---|---|
| `POST /api/auth/register` · `POST /api/auth/login` | — | 201/200 + JWT; 409 duplicate; 401 bad creds |
| `GET /api/auth/me` · `POST /api/auth/logout` | 🔒 | see §3 for logout semantics |
| `GET/POST /api/pantry` · `GET/PATCH/DELETE /api/pantry/{id}` | 🔒 | exact frontend contract; `DELETE?reason=&value=` logs waste |
| `GET /api/recipes/recommended` · `GET /api/recipes/{id}` | 🔒 | per-user feeds |
| `POST /api/recipes/{id}/cook` | 🔒 | 409 shortfall detail; never negative stock |
| `GET/POST /api/shopping` · `DELETE /api/shopping/{id}` | 🔒 | `inInventory` server-computed |
| `POST /api/shopping/checkout` | 🔒 | atomic; 409 empty list |
| `GET /api/purchases` · `GET /api/purchases/{id}` | 🔒 | real prices only |
| `POST /api/receipt/upload` | 🔒 | 415/413/400/503 validation ladder |
| `GET /api/analytics/summary` | 🔒 | honest-money analytics |
| `GET /api/health` | — | liveness + feature flags (no secrets) |

## 12 · Production safety

Strong-secret enforcement (§3) · env-driven CORS · generic 500 body
(internals logged, never returned) · Pydantic validation everywhere ·
content-based upload validation · ownership-scoped queries (404 over 403) ·
parameterized SQLAlchemy · atomic transactions · correct HTTP codes
(400/401/404/409/413/415/422/502/503).

## 13 · Known limitations

* **Logout does not revoke tokens server-side** (see §3).
* Refresh-token rotation not implemented — 7-day access tokens only.
* Bedrock prompt assumes the **Converse API**; exotic regions/models may
  need `BEDROCK_MODEL_ID` adjustments.
* OCR quality for handwritten receipts is limited by Textract.
* Waste `estimated_value` is per reported unit; multi-unit precision of
  receipt-derived prices (line-total ÷ qty) is best-effort.
* Alembic `batch_alter_table` mode is used for PostgreSQL/SQLite parity;
  very large existing tables might prefer native `ALTER` statements.
