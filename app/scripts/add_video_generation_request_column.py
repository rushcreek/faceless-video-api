"""
Migration script to add video_generation_request column to images table.
Run this script to update existing databases.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import engine
from sqlalchemy import text
from app.core.logging import logger

async def add_video_generation_request_column():
    """Add video_generation_request JSONB column to images table"""
    
    async with engine.begin() as conn:
        # Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'images' 
            AND column_name = 'video_generation_request'
        """)
        
        result = await conn.execute(check_query)
        exists = result.fetchone()
        
        if exists:
            logger.info("Column 'video_generation_request' already exists in images table")
            print("✓ Column 'video_generation_request' already exists")
            return
        
        # Add the column
        logger.info("Adding video_generation_request column to images table...")
        print("Adding video_generation_request column to images table...")
        
        alter_query = text("""
            ALTER TABLE images 
            ADD COLUMN video_generation_request JSONB
        """)
        
        await conn.execute(alter_query)
        
        logger.info("Successfully added video_generation_request column")
        print("✓ Successfully added video_generation_request column to images table")

async def main():
    """Run the migration"""
    try:
        logger.info("Starting migration: add video_generation_request column")
        print("\n" + "="*60)
        print("Migration: Add video_generation_request column to images")
        print("="*60 + "\n")
        
        await add_video_generation_request_column()
        
        print("\n✓ Migration completed successfully!\n")
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        print(f"\n✗ Migration failed: {e}\n")
        raise

if __name__ == "__main__":
    asyncio.run(main())
