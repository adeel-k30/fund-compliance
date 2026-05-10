"""Add s3 key and task_id and update status to enum

Revision ID: 4ae74f9d2690
Revises: 2183f5c289f6
Create Date: 2026-05-10 12:14:17.185047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ae74f9d2690'
down_revision: Union[str, Sequence[str], None] = '2183f5c289f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    uploadstatus = sa.Enum('pending', 'processing', 'complete', 'failed', name='uploadstatus')
    uploadstatus.create(op.get_bind())

    op.add_column('uploads', sa.Column('s3_key', sa.String(), nullable=True))
    op.add_column('uploads', sa.Column('task_id', sa.String(), nullable=True))
    op.alter_column('uploads', 'status',
        existing_type=sa.VARCHAR(),
        type_=sa.Enum('pending', 'processing', 'complete', 'failed', name='uploadstatus'),
        nullable=False,
        postgresql_using='status::uploadstatus'
    )

def downgrade() -> None:
    op.alter_column('uploads', 'status',
        existing_type=sa.Enum('pending', 'processing', 'complete', 'failed', name='uploadstatus'),
        type_=sa.VARCHAR(),
        nullable=True
    )
    op.drop_column('uploads', 'task_id')
    op.drop_column('uploads', 's3_key')
    # drop the enum type too
    sa.Enum(name='uploadstatus').drop(op.get_bind())
    # ### end Alembic commands ###
