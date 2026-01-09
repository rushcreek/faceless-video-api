"""Add runware_image_uuid column to track Runware's internal image identifiers

This is needed because Runware's video API only accepts image UUIDs (not URLs) for
the frameImages parameter. The CDN URLs expire after a TTL period, but UUIDs persist.

Revision ID: add_image_uuid_column
Revises: 
Create Date: 2025-01-15

"""
import asyncio
import sys
import os

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import text
from app.db.session import async_session
from app.core.logging import logger


async def upgrade():
    """Add runware_image_uuid column to images table"""
    async with async_session() as session:
        try:
            # Check if column already exists
            result = await session.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'images' AND column_name = 'runware_image_uuid'
            """))
            if result.fetchone():
                logger.info("Column 'runware_image_uuid' already exists, skipping...")
                return
            
            # Add the column
            await session.execute(text("""
                ALTER TABLE images ADD COLUMN runware_image_uuid VARCHAR(255) NULL
            """))
            
            # Create index for faster lookups
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_images_runware_image_uuid 
                ON images (runware_image_uuid)
            """))
            
            await session.commit()
            logger.info("✅ Successfully added 'runware_image_uuid' column to images table")
            
        except Exception as e:
            logger.error(f"❌ Error adding column: {e}")
            await session.rollback()
            raise


async def downgrade():
    """Remove runware_image_uuid column from images table"""
    async with async_session() as session:
        try:
            await session.execute(text("""
                DROP INDEX IF EXISTS idx_images_runware_image_uuid
            """))
            await session.execute(text("""
                ALTER TABLE images DROP COLUMN IF EXISTS runware_image_uuid
            """))
            await session.commit()
            logger.info("✅ Successfully removed 'runware_image_uuid' column from images table")
            
        except Exception as e:
            logger.error(f"❌ Error removing column: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    print("Adding 'runware_image_uuid' column to images table...")
    asyncio.run(upgrade())
