#!/usr/bin/env python3
"""
Check if a video generation task is complete by monitoring WebSocket messages.
"""

import asyncio
import websockets
import json
from dotenv import load_dotenv
import os

load_dotenv()

async def monitor_video_task(task_uuid, timeout=300):
    """Monitor a specific task UUID for completion"""
    
    api_key = os.getenv('RUNWARE_API_KEY')
    ws_url = "wss://ws-api.runware.ai/v1"
    extra_headers = {"Authorization": f"Bearer {api_key}"}
    
    print(f"Monitoring task: {task_uuid}")
    print(f"Timeout: {timeout}s")
    print("=" * 80)
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        async with websockets.connect(ws_url, additional_headers=extra_headers) as websocket:
            print("✅ Connected to Runware WebSocket")
            
            while True:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    print(f"\n⏱️  Timeout after {elapsed:.1f}s")
                    return None
                
                try:
                    # Wait for message
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(message)
                    
                    # Print all messages
                    if 'data' in data:
                        for item in data['data']:
                            if item.get('taskUUID') == task_uuid:
                                print(f"\n📨 Message for our task:")
                                print(json.dumps(item, indent=2))
                                
                                if 'videoURL' in item:
                                    video_url = item['videoURL']
                                    print(f"\n✅ VIDEO READY!")
                                    print(f"URL: {video_url}")
                                    if 'cost' in item:
                                        print(f"Cost: ${item['cost']}")
                                    return video_url
                            else:
                                # Print other messages briefly
                                task_type = item.get('taskType', 'unknown')
                                print(f"  [{task_type}] message received")
                    
                    elif 'errors' in data:
                        print(f"\n❌ Error received:")
                        print(json.dumps(data['errors'], indent=2))
                
                except asyncio.TimeoutError:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    print(f"  Waiting... ({elapsed:.0f}s elapsed)", end='\r')
                    continue
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

if __name__ == "__main__":
    # The task UUID from the first successful submission
    task_id = "d3f89d7e-21c3-4c09-acc9-f84af8510cae"
    result = asyncio.run(monitor_video_task(task_id, timeout=300))
