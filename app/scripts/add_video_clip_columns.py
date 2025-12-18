"""Add video clip tracking columns

Revision ID: add_video_clip_columns
Revises: 
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = 'add_video_clip_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to track video clip generation
    op.add_column('images', sa.Column('video_clip_task_uuid', sa.String(), nullable=True))
    op.add_column('images', sa.Column('video_clip_url', sa.String(), nullable=True))
    op.add_column('images', sa.Column('video_clip_status', sa.String(), nullable=True))
    op.add_column('images', sa.Column('video_clip_cost', sa.Float(), nullable=True))
    
    # Create index on video_clip_task_uuid for faster lookups
    op.create_index('idx_images_video_clip_task_uuid', 'images', ['video_clip_task_uuid'])


def downgrade():
    op.drop_index('idx_images_video_clip_task_uuid', table_name='images')
    op.drop_column('images', 'video_clip_cost')
    op.drop_column('images', 'video_clip_status')
    op.drop_column('images', 'video_clip_url')
    op.drop_column('images', 'video_clip_task_uuid')
