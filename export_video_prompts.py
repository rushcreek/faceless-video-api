#!/usr/bin/env python3
"""
Export video generation prompts from the database to a JSON file.
Usage: python export_video_prompts.py [task_id]
"""

import asyncio
import json
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

async def export_video_prompts(task_id=None):
    """Export video prompts for a task to JSON file"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment")
        return
    
    # Create synchronous engine for simple query
    engine = create_engine(database_url)
    
    if not task_id:
        # Get the most recent task
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT id, story_title FROM video_tasks ORDER BY created_at DESC LIMIT 1"
            ))
            row = result.fetchone()
            if row:
                task_id = row[0]
                story_title = row[1]
                print(f"Using most recent task: {story_title} ({task_id})")
            else:
                print("No tasks found in database")
                return
    
    # Get all scenes with video prompts
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                id,
                enhanced_prompt,
                video_generation_request,
                urls,
                created_at
            FROM images 
            WHERE task_id = :task_id 
            AND video_generation_request IS NOT NULL 
            AND video_generation_request::text != 'null'
            ORDER BY created_at
        """), {"task_id": task_id})
        
        scenes = []
        for row in result:
            scene_id, enhanced_prompt, video_request, urls, created_at = row
            
            # Parse the image URLs
            image_urls = json.loads(urls) if isinstance(urls, str) else urls
            first_image_url = image_urls[0] if image_urls and len(image_urls) > 0 else None
            
            # Parse video request
            video_req = json.loads(video_request) if isinstance(video_request, str) else video_request
            
            scene_data = {
                "scene_id": scene_id,
                "image_url": first_image_url,
                "enhanced_prompt": enhanced_prompt,
                "video_generation": video_req,
                "created_at": str(created_at)
            }
            scenes.append(scene_data)
    
    if not scenes:
        print(f"No video prompts found for task {task_id}")
        return
    
    # Create output
    output = {
        "task_id": task_id,
        "total_scenes": len(scenes),
        "scenes": scenes
    }
    
    # Write to file
    output_file = f"video_prompts_{task_id[:8]}.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Exported {len(scenes)} video prompts to: {output_file}")
    print(f"\nSummary:")
    for i, scene in enumerate(scenes, 1):
        prompt_preview = scene['video_generation']['prompt'][:80]
        print(f"  Scene {i}: {prompt_preview}...")
    
    # Also create Runware API ready format
    runware_requests = []
    for i, scene in enumerate(scenes):
        runware_req = {
            "taskType": "videoInference",
            "taskUUID": f"{task_id}-scene-{i}",
            "fps": 24,
            "model": "bytedance:2@1",
            "outputFormat": "mp4",
            "height": 864,
            "width": 480,
            "numberResults": 1,
            "includeCost": True,
            "outputQuality": 85,
            "providerSettings": {
                "bytedance": {
                    "cameraFixed": True
                }
            },
            "frameImages": [
                {
                    "inputImage": scene["image_url"]
                }
            ],
            "positivePrompt": scene["video_generation"]["prompt"],
            "duration": scene["video_generation"].get("duration", 5)
        }
        runware_requests.append(runware_req)
    
    runware_file = f"runware_requests_{task_id[:8]}.json"
    with open(runware_file, 'w') as f:
        json.dump(runware_requests, f, indent=2)
    
    print(f"\n✅ Created Runware API requests file: {runware_file}")
    print(f"\nTo test with Runware API, use:")
    print(f'curl --request POST \\')
    print(f'--url "https://api.runware.ai/v1" \\')
    print(f'--header "Authorization: Bearer YOUR_API_KEY" \\')
    print(f'--header "Content-Type: application/json" \\')
    print(f'--data @{runware_file}')

if __name__ == "__main__":
    task_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(export_video_prompts(task_id))
