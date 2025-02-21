"""empty message

Revision ID: 880ffbd71142
Revises: 
Create Date: 2025-02-21 16:20:56.118402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '880ffbd71142'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('referral_links', 'source')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('referral_links', sa.Column('source', sa.VARCHAR(), nullable=True))
    # ### end Alembic commands ###
