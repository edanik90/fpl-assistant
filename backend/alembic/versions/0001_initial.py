"""Initial schema for isolated synthetic snapshots and workspace notes."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(100), nullable=False, unique=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("season", sa.String(20), nullable=False),
        sa.Column("gameweek", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("bank_tenths", sa.Integer(), nullable=False),
        sa.Column("free_transfers", sa.Integer(), nullable=False),
        sa.CheckConstraint("bank_tenths >= 0"),
        sa.CheckConstraint("free_transfers >= 0"),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column("source_player_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("short_name", sa.String(40), nullable=False),
        sa.Column("club", sa.String(60), nullable=False),
        sa.Column("club_code", sa.String(3), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("position", sa.String(3), nullable=False),
        sa.Column("price_tenths", sa.Integer(), nullable=False),
        sa.UniqueConstraint("snapshot_id", "source_player_id"),
        sa.CheckConstraint("price_tenths >= 0"),
        sa.CheckConstraint("position IN ('GK', 'DEF', 'MID', 'FWD')"),
    )
    op.create_table(
        "picks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("is_captain", sa.Boolean(), nullable=False),
        sa.Column("is_vice_captain", sa.Boolean(), nullable=False),
        sa.Column("purchase_price_tenths", sa.Integer(), nullable=False),
        sa.Column("selling_price_tenths", sa.Integer(), nullable=False),
        sa.UniqueConstraint("snapshot_id", "slot"),
        sa.UniqueConstraint("snapshot_id", "player_id"),
        sa.CheckConstraint("slot BETWEEN 1 AND 15"),
        sa.CheckConstraint("purchase_price_tenths >= 0 AND selling_price_tenths >= 0"),
    )
    op.create_table(
        "fixtures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column("gameweek", sa.Integer(), nullable=False),
        sa.Column("home_club", sa.String(60), nullable=False),
        sa.Column("home_code", sa.String(3), nullable=False),
        sa.Column("away_club", sa.String(60), nullable=False),
        sa.Column("away_code", sa.String(3), nullable=False),
    )
    op.create_table(
        "workspace",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.CheckConstraint("id = 1"),
    )


def downgrade():
    for table in ("workspace", "fixtures", "picks", "players", "snapshots"):
        op.drop_table(table)
