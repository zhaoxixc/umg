"""add asset network fields

Revision ID: 3f2a1c9d5e01
Revises: fff5535aa732
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f2a1c9d5e01"
down_revision: Union[str, None] = "fff5535aa732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("ip_address", sa.String(64),
                                      nullable=False, server_default=""))
    op.add_column("assets", sa.Column("bmc_address", sa.String(64),
                                      nullable=False, server_default=""))
    op.add_column("assets", sa.Column("remark", sa.String(255),
                                      nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("assets", "remark")
    op.drop_column("assets", "bmc_address")
    op.drop_column("assets", "ip_address")
