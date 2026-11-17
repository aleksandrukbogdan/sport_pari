"""Source attribution and catalog team tags."""
import sqlalchemy as sa
from alembic import op

revision = "0004_news_sources"
down_revision = "0003_comment_visibility"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("news", sa.Column("team_ids", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("news", sa.Column("source_url", sa.String(2048)))
    op.add_column("news", sa.Column("source_name", sa.String(100)))
    op.create_index("ux_news_source_url", "news", ["source_url"], unique=True)


def downgrade():
    op.drop_index("ux_news_source_url", table_name="news")
    op.drop_column("news", "source_name")
    op.drop_column("news", "source_url")
    op.drop_column("news", "team_ids")
