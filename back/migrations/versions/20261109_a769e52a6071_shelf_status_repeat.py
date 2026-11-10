"""shelf status repeat

Revision ID: a769e52a6071
Revises: dbfe6e983e02
Create Date: 2026-11-09 13:08:40.440628
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a769e52a6071"
down_revision: str | None = "dbfe6e983e02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Новый статус шкафа «Хочу повторить». В Postgres 12+ ADD VALUE можно и внутри транзакции.
    op.execute("ALTER TYPE shelf_status ADD VALUE IF NOT EXISTS 'REPEAT'")


def downgrade() -> None:
    # Значение из enum Postgres не удалить — переводим такие чаи в «Закончился» и пересоздаём тип.
    op.execute("UPDATE shelf_items SET status = 'FINISHED' WHERE status = 'REPEAT'")
    op.execute("ALTER TYPE shelf_status RENAME TO shelf_status_old")
    op.execute("CREATE TYPE shelf_status AS ENUM ('WANT', 'HAVE', 'FINISHED')")
    op.execute("ALTER TABLE shelf_items ALTER COLUMN status TYPE shelf_status USING status::text::shelf_status")
    op.execute("DROP TYPE shelf_status_old")
