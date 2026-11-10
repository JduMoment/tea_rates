"""review tastes and astringency, wine to grape

Revision ID: 186a14b130ed
Revises: a769e52a6071
Create Date: 2026-11-09 15:22:00.490498
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "186a14b130ed"
down_revision: str | None = "a769e52a6071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Вкус, который автор отмечает сам (пусто — выводится из нот), и шкала терпкости
    op.add_column(
        "reviews",
        sa.Column(
            "tastes",
            postgresql.ARRAY(
                sa.Enum("SWEET", "SOUR", "SALTY", "BITTER", "UMAMI", name="taste", native_enum=False, length=16)
            ),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column("reviews", sa.Column("astringency", sa.SmallInteger(), nullable=True))
    op.create_check_constraint("ck_reviews_astringency", "reviews", "astringency BETWEEN 1 AND 5")
    # Ноты «вино» больше нет: в старых отзывах — «виноград» (если его там ещё не было)
    op.execute(
        """
        UPDATE reviews SET flavors = CASE
            WHEN 'GRAPE' = ANY(flavors) THEN array_remove(flavors, 'WINE')
            ELSE array_replace(flavors, 'WINE', 'GRAPE')
        END
        WHERE 'WINE' = ANY(flavors)
        """
    )


def downgrade() -> None:
    # «Вино» обратно не восстановить: какие «виноград» были им — неизвестно
    op.drop_constraint("ck_reviews_astringency", "reviews", type_="check")
    op.drop_column("reviews", "astringency")
    op.drop_column("reviews", "tastes")
