#!/usr/bin/env python3
"""
Migration script to convert enum columns to string columns and drop enum types.
This removes hardcoded database enums in favor of config-driven validation.
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

async def migrate():
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("Error: DATABASE_URL must be set")
        return
    
    # Parse connection string
    # Format: postgresql://user@host:port/database or postgresql://user:password@host:port/database
    url_without_scheme = database_url.replace('postgresql://', '')
    
    # Check if there's a password
    if '@' in url_without_scheme:
        user_part, host_part = url_without_scheme.split('@', 1)
        if ':' in user_part:
            user, password = user_part.split(':', 1)
        else:
            user = user_part
            password = None
    else:
        print("Error: Invalid DATABASE_URL format")
        return
    
    # Parse host and database
    if '/' in host_part:
        host_port, database = host_part.split('/', 1)
    else:
        print("Error: Invalid DATABASE_URL format - missing database name")
        return
    
    if ':' in host_port:
        host, port_str = host_port.split(':', 1)
        port = int(port_str)
    else:
        host = host_port
        port = 5432
    
    print(f"Connecting to database: {database} on {host}:{port} as {user}")
    
    # Build connection parameters
    conn_params = {
        'host': host,
        'port': port,
        'user': user,
        'database': database
    }
    
    if password:
        conn_params['password'] = password
    
    conn = await asyncpg.connect(**conn_params)
    
    try:
        print("\n=== Starting migration to convert enums to strings ===\n")
        
        # Step 1: Convert story_style_descriptor enum to string
        print("1. Converting story_style_descriptor from enum to string...")
        await conn.execute("""
            ALTER TABLE video_tasks 
            ALTER COLUMN story_style_descriptor TYPE VARCHAR 
            USING story_style_descriptor::text;
        """)
        print("   ✓ story_style_descriptor converted to string")
        
        # Step 2: Convert art_style enum to string
        print("2. Converting art_style from enum to string...")
        await conn.execute("""
            ALTER TABLE video_tasks 
            ALTER COLUMN art_style TYPE VARCHAR 
            USING art_style::text;
        """)
        print("   ✓ art_style converted to string")
        
        # Step 3: Convert duration enum to string
        print("3. Converting duration from enum to string...")
        await conn.execute("""
            ALTER TABLE video_tasks 
            ALTER COLUMN duration TYPE VARCHAR 
            USING duration::text;
        """)
        print("   ✓ duration converted to string")
        
        # Step 4: Convert voice_name enum to string
        print("4. Converting voice_name from enum to string...")
        await conn.execute("""
            ALTER TABLE video_tasks 
            ALTER COLUMN voice_name TYPE VARCHAR 
            USING voice_name::text;
        """)
        print("   ✓ voice_name converted to string")
        
        # Step 5: Convert language enum to string
        print("5. Converting language from enum to string...")
        await conn.execute("""
            ALTER TABLE video_tasks 
            ALTER COLUMN language TYPE VARCHAR 
            USING language::text;
        """)
        print("   ✓ language converted to string")
        
        # Step 6: Convert status enum to string
        print("6. Converting status from enum to string...")
        await conn.execute("""
            ALTER TABLE video_tasks 
            ALTER COLUMN status TYPE VARCHAR 
            USING status::text;
        """)
        print("   ✓ status converted to string")
        
        # Step 7: Drop all enum types
        print("\n7. Dropping enum types from database...")
        enum_types = [
            'story_style_descriptor',
            'art_style',
            'duration',
            'voice_name',
            'language',
            'status'
        ]
        
        for enum_type in enum_types:
            try:
                await conn.execute(f"DROP TYPE IF EXISTS {enum_type} CASCADE;")
                print(f"   ✓ Dropped enum type: {enum_type}")
            except Exception as e:
                print(f"   ⚠ Warning dropping {enum_type}: {e}")
        
        print("\n=== Migration completed successfully! ===")
        print("\nAll configuration options are now managed in config.json")
        print("Columns are now strings with runtime validation via Pydantic")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
