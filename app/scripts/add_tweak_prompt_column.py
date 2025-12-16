import asyncio
import logging
from app.db.session import async_session
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_tweak_prompt_column():
    """Add tweak_prompt column to video_tasks table"""
    async with async_session() as session:
        try:
            # Check if column already exists
            check_column = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='video_tasks' AND column_name='tweak_prompt'
            """)
            result = await session.execute(check_column)
            exists = result.fetchone()
            
            if exists:
                logger.info("tweak_prompt column already exists, skipping migration")
                return
            
            # Add the column
            logger.info("Adding tweak_prompt column to video_tasks table...")
            alter_table = text("""
                ALTER TABLE video_tasks 
                ADD COLUMN tweak_prompt TEXT
            """)
            await session.execute(alter_table)
            await session.commit()
            logger.info("Successfully added tweak_prompt column")
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(add_tweak_prompt_column())
