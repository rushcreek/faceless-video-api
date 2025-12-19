#!/usr/bin/env python3
"""
Database migration script to add image_generation_cost column to images table.
This tracks the cost of image generation API calls (separate from video_clip_cost).
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from app.db.session import async_session
from app.core.logging import logger


async def add_image_generation_cost_column():
    """Add image_generation_cost column to images table if it doesn't exist"""
    
    async with async_session() as session:
        try:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'images' 
                AND column_name = 'image_generation_cost'
            """)
            
            result = await session.execute(check_query)
            exists = result.fetchone() is not None
            
            if exists:
                logger.info("✅ Column 'image_generation_cost' already exists in images table")
                return
            
            # Add the column
            logger.info("Adding image_generation_cost column to images table...")
            alter_query = text("""
                ALTER TABLE images 
                ADD COLUMN image_generation_cost FLOAT DEFAULT NULL
            """)
            
            await session.execute(alter_query)
            await session.commit()
            
            logger.info("✅ Successfully added image_generation_cost column to images table")
            
        except Exception as e:
            logger.error(f"❌ Error adding image_generation_cost column: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(add_image_generation_cost_column())
