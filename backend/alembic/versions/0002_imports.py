"""Immutable imports, unknown prices, selected snapshot and correction history."""
from alembic import op
import sqlalchemy as sa

revision = "0002_imports"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("snapshots", table_args=(sa.CheckConstraint("bank_tenths >= 0"), sa.CheckConstraint("free_transfers >= 0"))) as batch:
        batch.alter_column("bank_tenths", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("free_transfers", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("label", sa.String(80), nullable=True))
        batch.add_column(sa.Column("captured_at", sa.String(40), nullable=True))
        batch.add_column(sa.Column("kind", sa.String(20), nullable=True))
        batch.add_column(sa.Column("import_data", sa.JSON(), nullable=True))
    with op.batch_alter_table("picks", table_args=(sa.CheckConstraint("slot BETWEEN 1 AND 15"), sa.CheckConstraint("purchase_price_tenths >= 0 AND selling_price_tenths >= 0"))) as batch:
        batch.alter_column("purchase_price_tenths", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("selling_price_tenths", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("fixtures") as batch:
        batch.alter_column("gameweek", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("source_fixture_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("kickoff_time", sa.String(40), nullable=True))
    op.create_table(
        "selection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.CheckConstraint("id = 1"),
    )
    op.create_table(
        "corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.UniqueConstraint("snapshot_id", "revision"),
    )


def downgrade():
    # Unknown values cannot safely be converted back to milestone 1's mandatory
    # prices. Restore a pre-upgrade backup instead of inventing monetary values.
    raise RuntimeError("Restore a milestone 1 database backup to downgrade.")
