"""
Add audio_duration column to images table
"""
import asyncio
import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from app.db.session import async_session
from app.core.logging import logger

async def add_audio_duration_column():
    """Add audio_duration column to images table"""
    try:
        async with async_session() as session:
            # Add audio_duration column
            await session.execute(text("""
                ALTER TABLE images 
                ADD COLUMN IF NOT EXISTS audio_duration FLOAT;
            """))
            
            await session.commit()
            logger.info("Successfully added audio_duration column to images table")
            
    except Exception as e:
        logger.error(f"Error adding audio_duration column: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(add_audio_duration_column())
    print("Migration completed successfully")
