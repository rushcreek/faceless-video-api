#!/usr/bin/env python3
"""
Simple test: Submit video request and monitor until complete.
"""

import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

async def generate_and_wait():
    api_key = os.getenv('RUNWARE_API_KEY')
    ws_url = "wss://ws-api.runware.ai/v1"
    extra_headers = {"Authorization": f"Bearer {api_key}"}
    
    # Simple 2-second test
    task_uuid = str(uuid.uuid4())
    request = {
        "taskType": "videoInference",
        "taskUUID": task_uuid,
        "fps": 24,
        "model": "bytedance:2@1",
        "outputFormat": "mp4",
        "height": 864,
        "width": 480,
        "numberResults": 1,
        "includeCost": True,
        "outputQuality": 85,
        "providerSettings": {"bytedance": {"cameraFixed": True}},
        "frameImages": [
            {"inputImage": "https://im.runware.ai/image/ws/2/ii/c9a0f823-e24b-418e-aa2b-c3d3c12426b5.jpg"}
        ],
        "positivePrompt": "Slow camera pan across cityscape, subtle movement of clouds and light",
        "duration": 2
    }
    
    print("=" * 80)
    print("🎬 GENERATING 2-SECOND VIDEO")
    print("=" * 80)
    print(f"Task UUID: {task_uuid}")
    print(f"Image: {request['frameImages'][0]['inputImage']}")
    print(f"Duration: {request['duration']}s")
    print("=" * 80)
    
    async with websockets.connect(ws_url, additional_headers=extra_headers) as ws:
        # Send request
        await ws.send(json.dumps([request]))
        print("✅ Request sent, waiting for video...")
        
        start = asyncio.get_event_loop().time()
        
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(msg)
                
                elapsed = int(asyncio.get_event_loop().time() - start)
                
                if 'data' in data:
                    for item in data['data']:
                        if item.get('taskUUID') == task_uuid:
                            if 'videoURL' in item:
                                print(f"\n{'=' * 80}")
                                print(f"✅ SUCCESS! ({elapsed}s)")
                                print(f"{'=' * 80}")
                                print(f"Video URL: {item['videoURL']}")
                                if 'cost' in item:
                                    print(f"Cost: ${item['cost']}")
                                print(f"{'=' * 80}")
                                return item['videoURL']
                            elif item.get('taskType') == 'videoInference':
                                print(f"  ⏳ Processing... ({elapsed}s)")
                
                if 'errors' in data:
                    print(f"\n❌ Error: {data['errors']}")
                    return None
                    
            except asyncio.TimeoutError:
                elapsed = int(asyncio.get_event_loop().time() - start)
                print(f"  ⏳ Still waiting... ({elapsed}s)", end='\r')
                
                if elapsed > 600:  # 10 min timeout
                    print(f"\n⏱️  Timeout after {elapsed}s")
                    return None

if __name__ == "__main__":
    result = asyncio.run(generate_and_wait())
