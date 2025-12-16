import asyncio
import logging
from app.db.session import async_session
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_caption_font_column():
    """Add caption_font column to video_tasks table"""
    async with async_session() as session:
        try:
            # Check if column already exists
            check_column = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='video_tasks' AND column_name='caption_font'
            """)
            result = await session.execute(check_column)
            exists = result.fetchone()
            
            if exists:
                logger.info("caption_font column already exists, skipping migration")
                return
            
            # Add the column
            logger.info("Adding caption_font column to video_tasks table...")
            alter_table = text("""
                ALTER TABLE video_tasks 
                ADD COLUMN caption_font VARCHAR DEFAULT 'BebasNeue'
            """)
            await session.execute(alter_table)
            await session.commit()
            logger.info("Successfully added caption_font column")
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(add_caption_font_column())
