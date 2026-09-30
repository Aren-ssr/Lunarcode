"""Add founder profile fields and one-time course purchases."""

from alembic import op
import sqlalchemy as sa


revision = "0002_course_access"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("display_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "course_purchases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_slug", sa.String(length=80), nullable=False),
        sa.Column("stripe_session_id", sa.String(length=128), nullable=False),
        sa.Column("purchased_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("stripe_session_id"),
        sa.UniqueConstraint("user_id", "course_slug", name="uq_user_course_purchase"),
    )
    op.create_index("ix_course_purchases_user_id", "course_purchases", ["user_id"])


def downgrade():
    op.drop_index("ix_course_purchases_user_id", table_name="course_purchases")
    op.drop_table("course_purchases")
    op.drop_column("users", "is_owner")
    op.drop_column("users", "display_name")
