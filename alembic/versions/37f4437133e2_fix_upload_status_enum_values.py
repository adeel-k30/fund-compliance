"""fix upload status enum values

Revision ID: 37f4437133e2
Revises: 4ae74f9d2690
Create Date: 2026-05-12 19:12:07.169409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37f4437133e2'
down_revision: Union[str, Sequence[str], None] = '4ae74f9d2690'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create the enum type first
    uploadstatus = sa.Enum('pending', 'processing', 'completed', 'failed', name='uploadstatus')
    uploadstatus.create(op.get_bind())

    # then add the column
    op.add_column('uploads', sa.Column(
        'status',
        sa.Enum('pending', 'processing', 'completed', 'failed', name='uploadstatus'),
        nullable=False,
        server_default='pending'
    ))


def downgrade() -> None:
    op.drop_column('uploads', 'status')
    sa.Enum(name='uploadstatus').drop(op.get_bind())
