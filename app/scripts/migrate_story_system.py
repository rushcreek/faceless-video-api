"""
Migration script to update story system:
1. Create new story_style_descriptor enum
2. Add new art styles to art_style enum
3. Add story_style_descriptor column
4. Migrate data from story_topic to story_style_descriptor
5. Drop old story_topic column
6. Make custom_story NOT NULL
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.session import engine
from sqlalchemy import text
from app.core.logging import logger


async def migrate_database():
    """Run the database migration"""
    
    async with engine.begin() as conn:
        try:
            logger.info("Starting database migration...")
            
            # Step 1: Create new story_style_descriptor enum
            logger.info("Creating story_style_descriptor enum...")
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE story_style_descriptor AS ENUM (
                        'dark', 'mysterious', 'uplifting', 'dramatic', 'whimsical',
                        'melancholic', 'suspenseful', 'inspirational', 'nostalgic',
                        'surreal', 'epic', 'intimate', 'energetic', 'calm', 'chaotic'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN 
                        RAISE NOTICE 'story_style_descriptor enum already exists, skipping';
                END $$;
            """))
            
            # Step 2: Add new art style values
            logger.info("Adding new art styles...")
            art_styles = [
                'oil-painting', 'watercolor', 'sketch', 'noir', 'cyberpunk',
                'fantasy', 'minimalist', 'impressionist', 'pop-art', 'steampunk'
            ]
            
            for style in art_styles:
                try:
                    await conn.execute(text(f"""
                        ALTER TYPE art_style ADD VALUE IF NOT EXISTS '{style}';
                    """))
                    logger.info(f"Added art style: {style}")
                except Exception as e:
                    logger.warning(f"Could not add {style} (may already exist): {e}")
            
            # Step 3: Add story_style_descriptor column
            logger.info("Adding story_style_descriptor column...")
            await conn.execute(text("""
                ALTER TABLE video_tasks 
                ADD COLUMN IF NOT EXISTS story_style_descriptor story_style_descriptor;
            """))
            
            # Step 4: Migrate data from story_topic to story_style_descriptor
            logger.info("Migrating story_topic data to story_style_descriptor...")
            await conn.execute(text("""
                UPDATE video_tasks 
                SET story_style_descriptor = (CASE 
                    WHEN story_topic = 'scary' THEN 'dark'
                    WHEN story_topic = 'mystery' THEN 'mysterious'
                    WHEN story_topic = 'bedtime' THEN 'calm'
                    WHEN story_topic = 'interesting history' THEN 'dramatic'
                    WHEN story_topic = 'urban legends' THEN 'suspenseful'
                    WHEN story_topic = 'motivational' THEN 'inspirational'
                    WHEN story_topic = 'fun facts' THEN 'energetic'
                    WHEN story_topic = 'long form jokes' THEN 'whimsical'
                    WHEN story_topic = 'life pro tips' THEN 'uplifting'
                    WHEN story_topic = 'philosophy' THEN 'inspirational'
                    WHEN story_topic = 'love' THEN 'intimate'
                    WHEN story_topic = 'custom topic' THEN 'dramatic'
                    ELSE 'dramatic'
                END)::story_style_descriptor
                WHERE story_topic IS NOT NULL AND story_style_descriptor IS NULL;
            """))
            
            # Step 5: Drop story_topic column
            logger.info("Dropping story_topic column...")
            await conn.execute(text("""
                ALTER TABLE video_tasks DROP COLUMN IF EXISTS story_topic;
            """))
            
            # Step 6: Drop old story_topic enum type
            logger.info("Dropping story_topic enum type...")
            await conn.execute(text("""
                DROP TYPE IF EXISTS story_topic CASCADE;
            """))
            
            # Step 7: Set default value for existing NULL custom_story rows
            logger.info("Setting default for NULL custom_story values...")
            await conn.execute(text("""
                UPDATE video_tasks 
                SET custom_story = 'Legacy story content' 
                WHERE custom_story IS NULL;
            """))
            
            # Step 8: Make custom_story NOT NULL
            logger.info("Making custom_story NOT NULL...")
            await conn.execute(text("""
                ALTER TABLE video_tasks 
                ALTER COLUMN custom_story SET NOT NULL;
            """))
            
            logger.info("✅ Database migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise


async def main():
    """Main entry point"""
    try:
        await migrate_database()
        logger.info("Migration script finished successfully")
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
