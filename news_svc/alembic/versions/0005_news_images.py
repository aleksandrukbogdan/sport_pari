"""Optional source-provided article images."""

import sqlalchemy as sa

from alembic import op

revision = "0005_news_images"
down_revision = "0004_news_sources"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("news", sa.Column("image_url", sa.String(2048)))


def downgrade():
    op.drop_column("news", "image_url")
