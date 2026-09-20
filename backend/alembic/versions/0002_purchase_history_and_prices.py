"""Purchase history, real prices, food-name snapshots.

Revision ID: 0002_purchase_history
Revises: 0001_initial
Create Date: 2026-09-19 12:00:00 UTC

NON-DESTRUCTIVE:
* purchase_items        — NEW table
* purchases             — purchase_date RENAMED to purchased_at (data kept),
                          currency + source columns ADDED
* pantry_items          — purchase_price, currency, purchase_id ADDED,
                          CHECK quantity >= 0 ADDED
* shopping_items        — unit_price, currency ADDED, CHECK quantity > 0
* consumption_logs      — food_name snapshot ADDED
* waste_logs            — food_name snapshot ADDED

Existing rows are fully preserved; all new columns are nullable.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_purchase_history"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── purchases: rename + new columns (batch mode → SQLite-safe) ────
    with op.batch_alter_table("purchases") as batch:
        batch.alter_column(
            "purchase_date", new_column_name="purchased_at", nullable=True
        )
        batch.add_column(sa.Column("currency", sa.String(length=3), nullable=True))
        batch.add_column(
            sa.Column(
                "source", sa.String(length=30), nullable=False,
                server_default="checkout",
            )
        )
    op.create_index("ix_purchases_user_time", "purchases", ["user_id", "purchased_at"])

    # ── purchase_items — the new price-aware line table ───────────────
    op.create_table(
        "purchase_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purchase_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_items_purchase_id", "purchase_items", ["purchase_id"])

    # ── pantry_items: optional real price + source purchase ──────────
    with op.batch_alter_table("pantry_items") as batch:
        batch.add_column(sa.Column("purchase_price", sa.Numeric(12, 2), nullable=True))
        batch.add_column(sa.Column("currency", sa.String(length=3), nullable=True))
        batch.add_column(sa.Column("purchase_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_pantry_items_purchase_id",
            "purchases",
            ["purchase_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_check_constraint(
            "ck_pantry_items_quantity_non_negative", "quantity >= 0"
        )

    # ── shopping_items: optional real price carried into checkout ────
    with op.batch_alter_table("shopping_items") as batch:
        batch.add_column(sa.Column("unit_price", sa.Numeric(12, 2), nullable=True))
        batch.add_column(sa.Column("currency", sa.String(length=3), nullable=True))
        batch.create_check_constraint(
            "ck_shopping_items_quantity_positive", "quantity > 0"
        )

    # ── log snapshots: history survives pantry-item deletion ─────────
    with op.batch_alter_table("consumption_logs") as batch:
        batch.add_column(sa.Column("food_name", sa.String(length=200), nullable=True))
    with op.batch_alter_table("waste_logs") as batch:
        batch.add_column(sa.Column("food_name", sa.String(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("waste_logs") as batch:
        batch.drop_column("food_name")
    with op.batch_alter_table("consumption_logs") as batch:
        batch.drop_column("food_name")

    with op.batch_alter_table("shopping_items") as batch:
        batch.drop_constraint("ck_shopping_items_quantity_positive", type_="check")
        batch.drop_column("currency")
        batch.drop_column("unit_price")

    with op.batch_alter_table("pantry_items") as batch:
        batch.drop_constraint("ck_pantry_items_quantity_non_negative", type_="check")
        batch.drop_constraint("fk_pantry_items_purchase_id", type_="foreignkey")
        batch.drop_column("purchase_id")
        batch.drop_column("currency")
        batch.drop_column("purchase_price")

    op.drop_index("ix_purchase_items_purchase_id", table_name="purchase_items")
    op.drop_table("purchase_items")

    op.drop_index("ix_purchases_user_time", table_name="purchases")
    with op.batch_alter_table("purchases") as batch:
        batch.drop_column("source")
        batch.drop_column("currency")
        batch.alter_column(
            "purchased_at", new_column_name="purchase_date", nullable=True
        )
