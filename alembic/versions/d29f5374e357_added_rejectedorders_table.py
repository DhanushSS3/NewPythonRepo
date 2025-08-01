"""added rejectedorders table

Revision ID: d29f5374e357
Revises: 
Create Date: 2025-07-22 03:45:46.287345

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd29f5374e357'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('rejected_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rejected_id', mysql.VARCHAR(length=64), nullable=False),
    sa.Column('order_company_name', mysql.VARCHAR(length=255), nullable=False),
    sa.Column('order_type', mysql.VARCHAR(length=20), nullable=False),
    sa.Column('order_quantity', sa.DECIMAL(precision=18, scale=8), nullable=False),
    sa.Column('rejected_price', sa.DECIMAL(precision=18, scale=8), nullable=False),
    sa.Column('order_user_id', sa.Integer(), nullable=False),
    sa.Column('rejection_reason', mysql.VARCHAR(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('order_id', mysql.VARCHAR(charset='utf8mb4', collation='utf8mb4_general_ci', length=64), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['user_orders.order_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['order_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rejected_orders_id'), 'rejected_orders', ['id'], unique=False)
    op.create_index(op.f('ix_rejected_orders_order_id'), 'rejected_orders', ['order_id'], unique=False)
    op.create_index(op.f('ix_rejected_orders_order_user_id'), 'rejected_orders', ['order_user_id'], unique=False)
    op.create_index(op.f('ix_rejected_orders_rejected_id'), 'rejected_orders', ['rejected_id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_rejected_orders_rejected_id'), table_name='rejected_orders')
    op.drop_index(op.f('ix_rejected_orders_order_user_id'), table_name='rejected_orders')
    op.drop_index(op.f('ix_rejected_orders_order_id'), table_name='rejected_orders')
    op.drop_index(op.f('ix_rejected_orders_id'), table_name='rejected_orders')
    op.drop_table('rejected_orders')
    # ### end Alembic commands ###
