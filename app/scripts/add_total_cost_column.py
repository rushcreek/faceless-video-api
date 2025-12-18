"""
Migration script to add total_cost column to video_tasks table
"""
import asyncio
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from app.db.session import async_session
from app.core.logging import logger


async def add_total_cost_column():
    """Add total_cost column to video_tasks table if it doesn't exist"""
    try:
        async with async_session() as session:
            # Check if column exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='video_tasks' AND column_name='total_cost'
            """)
            result = await session.execute(check_query)
            exists = result.fetchone() is not None
            
            if exists:
                logger.info("total_cost column already exists in video_tasks table")
                return
            
            # Add the column
            logger.info("Adding total_cost column to video_tasks table...")
            alter_query = text("""
                ALTER TABLE video_tasks 
                ADD COLUMN total_cost FLOAT DEFAULT 0.0
            """)
            await session.execute(alter_query)
            await session.commit()
            
            logger.info("✅ Successfully added total_cost column to video_tasks table")
            
    except Exception as e:
        logger.error(f"Error adding total_cost column: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(add_total_cost_column())
