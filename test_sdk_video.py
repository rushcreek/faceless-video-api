"""
Test the new SDK-based video generation
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.runware_video_sdk import generate_video_from_image
from app.core.logging import logger

async def main():
    # Test with cityscape image
    image_url = "https://im.runware.ai/image/ws/2/ii/c9a0f823-e24b-418e-aa2b-c3d3c12426b5.jpg"
    prompt = "The video starts with a slow, smooth pan across a bustling cityscape at dawn. The camera captures the interplay of light and shadow on building facades as the first rays of sunlight illuminate the scene."
    
    logger.info("Testing SDK-based video generation...")
    logger.info(f"Image: {image_url}")
    logger.info(f"Prompt: {prompt}")
    
    video_url = await generate_video_from_image(
        image_url=image_url,
        prompt=prompt,
        duration=2,
        fps=24
    )
    
    if video_url:
        print(f"\n✅ SUCCESS! Video URL: {video_url}\n")
    else:
        print(f"\n❌ FAILED to generate video\n")

if __name__ == "__main__":
    asyncio.run(main())
