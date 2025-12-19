#!/usr/bin/env python3
"""
Test Runware video generation with a single scene.
"""

import asyncio
import json
from app.services.runware_video import generate_video_from_image

async def test_single_video():
    """Test generating a video for the first scene"""
    
    # Load the runware requests
    with open('runware_requests_709841fb.json', 'r') as f:
        requests = json.load(f)
    
    if not requests:
        print("No requests found in file")
        return
    
    # Test with first scene
    first_request = requests[0]
    
    print("=" * 80)
    print("TESTING VIDEO GENERATION")
    print("=" * 80)
    print(f"Image: {first_request['frameImages'][0]['inputImage']}")
    print(f"Prompt: {first_request['positivePrompt'][:100]}...")
    print(f"Duration: {first_request['duration']}s")
    print("=" * 80)
    
    video_url = await generate_video_from_image(
        image_url=first_request['frameImages'][0]['inputImage'],
        prompt=first_request['positivePrompt'],
        duration=first_request['duration'],
        timeout=120  # 2 minutes
    )
    
    if video_url:
        print("\n" + "=" * 80)
        print("✅ SUCCESS!")
        print("=" * 80)
        print(f"Video URL: {video_url}")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ FAILED")
        print("=" * 80)
    
    return video_url

if __name__ == "__main__":
    result = asyncio.run(test_single_video())
