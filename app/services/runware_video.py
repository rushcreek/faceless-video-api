import aiohttp
import asyncio
import websockets
import json as json_lib
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging import logger
from dotenv import load_dotenv
import uuid

load_dotenv()


async def generate_video_from_image(
    image_url: str,
    prompt: str,
    duration: int = 2,
    fps: int = 24,
    width: int = 480,
    height: int = 864,
    camera_fixed: bool = True,
    max_retries: int = 3,
    timeout: int = 300  # Increased to 5 minutes
) -> Optional[str]:
    """
    Generate a video from a static image using Runware API WebSocket.
    
    Args:
        image_url: URL of the input image
        prompt: Positive prompt describing the desired video motion
        duration: Video duration in seconds (default: 2)
        fps: Frames per second (default: 24)
        width: Video width in pixels (default: 480)
        height: Video height in pixels (default: 864)
        camera_fixed: Whether to keep camera fixed (default: True)
        max_retries: Maximum number of retry attempts
        timeout: Maximum time to wait for video generation in seconds
        
    Returns:
        URL of the generated video, or None if failed
    """
    
    if not settings.RUNWARE_API_KEY:
        logger.error("RUNWARE_API_KEY not configured")
        return None
    
    # Runware uses WebSocket API with authentication in extra_headers
    ws_url = "wss://ws-api.runware.ai/v1"
    
    # Extra headers for authentication
    extra_headers = {
        "Authorization": f"Bearer {settings.RUNWARE_API_KEY}"
    }
    
    # Generate a unique task UUID
    task_uuid = str(uuid.uuid4())
    
    payload = {
        "taskType": "videoInference",
        "taskUUID": task_uuid,
        "fps": fps,
        "model": "bytedance:2@1",
        "outputFormat": "mp4",
        "height": height,
        "width": width,
        "numberResults": 1,
        "includeCost": True,
        "outputQuality": 85,
        "providerSettings": {
            "bytedance": {
                "cameraFixed": camera_fixed
            }
        },
        "frameImages": [
            {
                "inputImage": image_url
            }
        ],
        "positivePrompt": prompt,
        "duration": duration
    }
    
    for attempt in range(max_retries):
        try:
            # Generate a fresh UUID for each attempt to avoid conflicts
            task_uuid = str(uuid.uuid4())
            payload["taskUUID"] = task_uuid
            
            logger.info(f"Generating video from image via WebSocket (attempt {attempt + 1}/{max_retries})")
            logger.debug(f"Image URL: {image_url}")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            async with websockets.connect(ws_url, additional_headers=extra_headers) as websocket:
                # Send the video generation request
                await websocket.send(json_lib.dumps([payload]))
                logger.info(f"Video generation request sent with UUID: {task_uuid}")
                
                # Wait for responses
                start_time = asyncio.get_event_loop().time()
                while True:
                    # Check timeout
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        logger.error(f"Timeout waiting for video generation after {timeout}s")
                        break
                    
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json_lib.loads(message)
                        logger.debug(f"Received WebSocket message: {data}")
                        
                        if isinstance(data, dict):
                            # Check for error
                            if 'error' in data:
                                logger.error(f"Runware API error: {data['error']}")
                                return None
                            
                            # Check if this is our video result
                            if data.get('taskUUID') == task_uuid:
                                if 'videoURL' in data:
                                    video_url = data['videoURL']
                                    logger.info(f"Video generated successfully: {video_url}")
                                    if 'cost' in data:
                                        logger.info(f"Video generation cost: ${data['cost']}")
                                    return video_url
                                elif 'status' in data:
                                    logger.info(f"Video generation status: {data['status']}")
                        
                        elif isinstance(data, list):
                            # Handle list of results
                            for item in data:
                                if isinstance(item, dict) and item.get('taskUUID') == task_uuid:
                                    if 'videoURL' in item:
                                        video_url = item['videoURL']
                                        logger.info(f"Video generated successfully: {video_url}")
                                        if 'cost' in item:
                                            logger.info(f"Video generation cost: ${item['cost']}")
                                        return video_url
                    
                    except asyncio.TimeoutError:
                        logger.debug("Waiting for video generation...")
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket connection closed")
                        break
                        
        except Exception as e:
            logger.error(f"Exception in generate_video_from_image (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                return None
    
    return None


async def test_video_generation():
    """
    Test function to generate a video from a sample image.
    """
    test_image_url = "https://v3b.fal.media/files/b/0a8691c8/k5G1VyD8tyIlZe6iux_Og.jpg"
    test_prompt = "Have the subjects in the middle of the frame, the woman with voluminous, black hair, look directly at the camera and hold up her phone with one hand and point to it with the other. Highly detailed matte fantasy painting, stormy lighting."
    
    logger.info("Testing Runware video generation...")
    video_url = await generate_video_from_image(
        image_url=test_image_url,
        prompt=test_prompt,
        duration=2
    )
    
    if video_url:
        logger.info(f"Test video generated: {video_url}")
    else:
        logger.error("Test video generation failed")
    
    return video_url


if __name__ == "__main__":
    # Run test
    asyncio.run(test_video_generation())
