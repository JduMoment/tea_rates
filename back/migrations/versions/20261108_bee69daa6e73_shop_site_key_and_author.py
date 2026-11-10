"""Магазины: нормализованный сайт (уникальный — против дублей) и автор.

Существующим магазинам ключ сайта считается из site. Если два магазина уже указывают
на один сайт — миграция остановится и назовёт их: дубли нужно слить вручную.

Revision ID: bee69daa6e73
Revises: 70ce6e046ed0
Create Date: 2026-11-08 16:50:48.081150
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from back.core.shop_url import shop_key

revision: str = "bee69daa6e73"
down_revision: str | None = "70ce6e046ed0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("shops", sa.Column("site_key", sa.String(length=255), nullable=True))
    op.add_column("shops", sa.Column("author_id", sa.Integer(), nullable=True))

    conn = op.get_bind()
    keys: dict[str, str] = {}
    for shop_id, name, site in conn.execute(sa.text("select id, name, site from shops")):
        key = shop_key(site)
        if key in keys:
            raise RuntimeError(f"Магазины {keys[key]} и {name} указывают на один сайт ({key}) — слейте дубли")
        keys[key] = name
        conn.execute(sa.text("update shops set site_key = :k where id = :id"), {"k": key, "id": shop_id})

    op.alter_column("shops", "site_key", nullable=False)
    op.create_unique_constraint("shops_site_key_key", "shops", ["site_key"])
    op.create_index(op.f("ix_shops_author_id"), "shops", ["author_id"], unique=False)
    op.create_foreign_key("shops_author_id_fkey", "shops", "users", ["author_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("shops_author_id_fkey", "shops", type_="foreignkey")
    op.drop_index(op.f("ix_shops_author_id"), table_name="shops")
    op.drop_constraint("shops_site_key_key", "shops", type_="unique")
    op.drop_column("shops", "author_id")
    op.drop_column("shops", "site_key")
