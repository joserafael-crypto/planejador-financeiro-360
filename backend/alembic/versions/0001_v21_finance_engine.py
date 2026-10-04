"""V2.1 finance engine initial schema."""
from alembic import op
from app.db.session import Base
from app.models import models

revision = "0001_v21_finance_engine"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
