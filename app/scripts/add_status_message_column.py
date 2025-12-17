"""
Migration script to add status_message column to video_tasks table
"""
import asyncio
from sqlalchemy import text
from app.db.session import async_session
from app.core.logging import logger


async def add_status_message_column():
    """Add status_message column to video_tasks table if it doesn't exist"""
    async with async_session() as session:
        try:
            # Check if column exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'video_tasks' 
                AND column_name = 'status_message'
            """)
            result = await session.execute(check_query)
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                logger.info("Adding status_message column to video_tasks table...")
                
                # Add the column
                alter_query = text("""
                    ALTER TABLE video_tasks 
                    ADD COLUMN status_message VARCHAR
                """)
                await session.execute(alter_query)
                await session.commit()
                
                logger.info("Successfully added status_message column")
            else:
                logger.info("status_message column already exists")
                
        except Exception as e:
            logger.error(f"Error adding status_message column: {str(e)}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(add_status_message_column())
