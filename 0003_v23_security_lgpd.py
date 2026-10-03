"""V2.3 security, sessions and LGPD controls."""
from alembic import op
import sqlalchemy as sa

revision="0003_v23_security_lgpd"
down_revision="0002_v22_intelligence"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("audit_logs", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(length=512), nullable=True))
    op.create_index("ix_audit_logs_user_id","audit_logs",["user_id"])
    op.create_index("ix_audit_logs_action","audit_logs",["action"])
    op.create_index("ix_audit_logs_created_at","audit_logs",["created_at"])
    op.create_table("sessions",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("token_hash",sa.String(length=128),nullable=False,unique=True),
        sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.Column("expires_at",sa.DateTime(),nullable=False),
        sa.Column("last_used_at",sa.DateTime(),nullable=False),
        sa.Column("revoked_at",sa.DateTime(),nullable=True),
        sa.Column("ip_address",sa.String(length=64),nullable=True),
        sa.Column("user_agent",sa.String(length=512),nullable=True),
    )
    op.create_index("ix_sessions_user_id","sessions",["user_id"])
    op.create_index("ix_sessions_token_hash","sessions",["token_hash"],unique=True)
    op.create_index("ix_sessions_expires_at","sessions",["expires_at"])
    op.create_index("ix_sessions_revoked_at","sessions",["revoked_at"])
    op.create_table("consents",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("purpose",sa.String(length=100),nullable=False),
        sa.Column("granted",sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column("version",sa.String(length=32),nullable=False),
        sa.Column("granted_at",sa.DateTime(),nullable=True),
        sa.Column("revoked_at",sa.DateTime(),nullable=True),
        sa.Column("created_at",sa.DateTime(),nullable=False),
    )
    op.create_index("ix_consents_user_id","consents",["user_id"])
    op.create_index("ix_consents_purpose","consents",["purpose"])
    op.create_index("ix_consent_user_purpose","consents",["user_id","purpose"])

def downgrade():
    op.drop_index("ix_consent_user_purpose",table_name="consents")
    op.drop_index("ix_consents_purpose",table_name="consents")
    op.drop_index("ix_consents_user_id",table_name="consents")
    op.drop_table("consents")
    op.drop_index("ix_sessions_revoked_at",table_name="sessions")
    op.drop_index("ix_sessions_expires_at",table_name="sessions")
    op.drop_index("ix_sessions_token_hash",table_name="sessions")
    op.drop_index("ix_sessions_user_id",table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_audit_logs_created_at",table_name="audit_logs")
    op.drop_index("ix_audit_logs_action",table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id",table_name="audit_logs")
    op.drop_column("audit_logs","user_agent")
    op.drop_column("audit_logs","ip_address")
