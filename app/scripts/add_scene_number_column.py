"""
Migration script to add scene_number column to images table
"""
import asyncio
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.db.session import async_session
from app.core.logging import logger

async def add_scene_number_column():
    """Add scene_number column to images table"""
    async with async_session() as session:
        try:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'images' 
                AND column_name = 'scene_number'
            """)
            result = await session.execute(check_query)
            exists = result.fetchone()
            
            if exists:
                logger.info("Column 'scene_number' already exists in images table")
                return
            
            # Add the column
            logger.info("Adding scene_number column to images table...")
            alter_query = text("""
                ALTER TABLE images 
                ADD COLUMN scene_number INTEGER;
            """)
            await session.execute(alter_query)
            
            # Create index for better query performance
            logger.info("Creating index on scene_number column...")
            index_query = text("""
                CREATE INDEX IF NOT EXISTS idx_images_scene_number 
                ON images(scene_number);
            """)
            await session.execute(index_query)
            
            await session.commit()
            logger.info("✅ Successfully added scene_number column and index")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Error adding scene_number column: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(add_scene_number_column())
    print("Migration completed!")
