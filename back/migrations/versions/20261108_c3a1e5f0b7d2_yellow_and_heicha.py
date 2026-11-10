"""Новые виды чая: жёлтый и хэй ча.

Значения добавляются в Postgres-enum tea_kind и сразу заводятся строками в categories.
ALTER TYPE ... ADD VALUE нельзя использовать в той же транзакции, где значение добавлено,
поэтому ADD VALUE — в autocommit-блоке.

Откат удаляет строки categories (если в видах нет чаёв — иначе упадёт на RESTRICT),
но значения enum остаются: Postgres не умеет удалять значения enum, а лишние не мешают.

Revision ID: c3a1e5f0b7d2
Revises: bee69daa6e73
Create Date: 2026-11-08 22:10:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c3a1e5f0b7d2"
down_revision: str | None = "bee69daa6e73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_KINDS = ("YELLOW", "HEICHA")


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for kind in NEW_KINDS:
            op.execute(f"ALTER TYPE tea_kind ADD VALUE IF NOT EXISTS '{kind}'")
    for kind in NEW_KINDS:
        op.execute(f"INSERT INTO categories (name) VALUES ('{kind}') ON CONFLICT (name) DO NOTHING")


def downgrade() -> None:
    names = ", ".join(f"'{k}'" for k in NEW_KINDS)
    op.execute(f"DELETE FROM categories WHERE name IN ({names})")
