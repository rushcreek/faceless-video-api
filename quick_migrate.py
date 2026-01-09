"""Quick migration to add runware_image_uuid column"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

import psycopg2

print("Connecting to database...")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')[:50]}...")

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'), connect_timeout=5)
    print("Connected!")
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name = 'images' AND column_name = 'runware_image_uuid'
    """)
    exists = cursor.fetchone()[0] > 0
    
    if exists:
        print("Column already exists")
    else:
        cursor.execute("ALTER TABLE images ADD COLUMN runware_image_uuid VARCHAR(255)")
        cursor.execute("CREATE INDEX idx_images_runware_image_uuid ON images (runware_image_uuid)")
        conn.commit()
        print("Column added successfully!")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
