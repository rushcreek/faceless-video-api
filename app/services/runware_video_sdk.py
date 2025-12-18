"""
Runware video generation service using Runware SDK (cleaner approach)
"""
import asyncio
from typing import Optional
from sqlalchemy.future import select
from app.core.config import settings
from app.core.logging import logger
from runware import Runware, IVideoInference, IFrameImage, IBytedanceProviderSettings


async def generate_video_from_image(
    image_url: str,
    prompt: str,
    duration: int = 2,
    fps: int = 24,
    width: int = 480,
    height: int = 864,
    max_retries: int = 3,
    db_session = None,
    image_id: str = None
) -> Optional[str]:
    """
    Generate a video from an image using Runware's bytedance:2@1 model via SDK
    
    Args:
        image_url: URL of the input image
        prompt: Text prompt for video generation
        duration: Video duration in seconds (default: 2)
        fps: Frames per second (default: 24)
        width: Video width (default: 480)
        height: Video height (default: 864)
        max_retries: Maximum number of retry attempts (default: 3)
        db_session: Database session for cancellation checks
        image_id: Image ID for cancellation checks
    
    Returns:
        URL of generated video or None if failed/cancelled
    """
    
    for attempt in range(max_retries):
        runware = None
        try:
            logger.info(f"🎬 Runware SDK: Generating video from image (attempt {attempt + 1}/{max_retries})")
            logger.info(f"   Image URL: {image_url}")
            logger.info(f"   Prompt: {prompt}")
            logger.info(f"   Duration: {duration}s ⏱️")
            logger.info(f"   FPS: {fps}")
            logger.info(f"   Dimensions: {width}x{height}")
            
            # Validate duration
            if not isinstance(duration, int):
                logger.warning(f"   ⚠️ Duration must be integer, got {type(duration)}. Converting...")
                duration = int(duration)
            
            if duration < 1 or duration > 10:
                logger.warning(f"   ⚠️ Duration {duration}s out of range (1-10), capping")
                duration = max(1, min(10, duration))
            
            logger.info(f"   ✅ Final duration for API: {duration}s")
            
            # Initialize Runware client
            runware = Runware(api_key=settings.RUNWARE_API_KEY)
            await runware.connect()
            
            # Prepare video generation request
            request_video = IVideoInference(
                model="bytedance:2@1",
                positivePrompt=prompt,
                duration=duration,
                fps=fps,
                width=width,
                height=height,
                frameImages=[IFrameImage(inputImage=image_url)],
                providerSettings=IBytedanceProviderSettings(cameraFixed=True),
                outputFormat="MP4",
                uploadEndpoint="runway"
            )
            
            logger.info(f"   📤 Request parameters:")
            logger.info(f"      Model: bytedance:2@1")
            logger.info(f"      Duration: {duration}s")
            logger.info(f"      FPS: {fps}")
            logger.info(f"      Total frames: {duration * fps}")
            
            # Generate video - SDK handles WebSocket connection internally
            logger.info("   🚀 Sending video generation request...")
            result = await runware.videoInference(requestVideo=request_video)
            
            # Check if result is async task response (video still processing)
            if hasattr(result, '__class__') and 'IAsyncTaskResponse' in str(result.__class__):
                task_uuid = result.taskUUID
                logger.info(f"   ✅ Video generation task submitted successfully")
                logger.info(f"      TaskUUID: {task_uuid}")
                logger.info(f"      Expected generation time: ~{duration * 30} seconds")
                logger.info(f"   ⏳ Polling for completion...")
                
                # Poll for results - optimized for 90-second generation time
                max_poll_attempts = 60  # 60 attempts * 3 seconds = 3 minutes max
                poll_interval = 3  # seconds - faster polling for quicker response
                
                for poll_attempt in range(max_poll_attempts):
                    # Check if task was cancelled (Option 1: Stop polling)
                    if db_session and image_id:
                        from app.models.image import Image
                        result = await db_session.execute(
                            select(Image).where(Image.id == image_id)
                        )
                        image = result.scalar_one_or_none()
                        
                        if image and image.video_clip_status in ['failed', 'cancelled']:
                            logger.info(f"Task {task_uuid} cancelled by user. Stopping polling.")
                            return None
                    
                    await asyncio.sleep(poll_interval)
                    
                    try:
                        # Try to get the completed video
                        videos = await runware.getResponse(taskUUID=task_uuid, numberResults=1)
                        
                        if videos and len(videos) > 0:
                            # Extract URL from response
                            video_url = None
                            if hasattr(videos[0], 'videoURL'):
                                video_url = videos[0].videoURL
                            elif hasattr(videos[0], 'video_url'):
                                video_url = videos[0].video_url
                            elif hasattr(videos[0], 'url'):
                                video_url = videos[0].url
                            elif isinstance(videos[0], dict):
                                video_url = videos[0].get('videoURL') or videos[0].get('video_url') or videos[0].get('url')
                            
                            if video_url:
                                logger.info(f"✅ Video generated successfully: {video_url}")
                                return video_url
                    except Exception as poll_error:
                        # Task not ready yet, continue polling
                        logger.debug(f"Poll attempt {poll_attempt + 1}/{max_poll_attempts}: {poll_error}")
                        continue
                
                logger.error(f"❌ Timeout: Video not ready after {max_poll_attempts * poll_interval} seconds")
                return None
            
            # Handle synchronous response (list of videos) - unlikely for video
            if result and isinstance(result, list) and len(result) > 0:
                video_url = None
                if hasattr(result[0], 'videoURL'):
                    video_url = result[0].videoURL
                elif hasattr(result[0], 'video_url'):
                    video_url = result[0].video_url
                elif hasattr(result[0], 'url'):
                    video_url = result[0].url
                elif isinstance(result[0], dict):
                    video_url = result[0].get('videoURL') or result[0].get('video_url') or result[0].get('url')
                
                if video_url:
                    logger.info(f"✅ Video generated successfully: {video_url}")
                    return video_url
            
            logger.error(f"❌ Unexpected response type: {type(result)}")
            logger.debug(f"Response: {result}")
            return None
        
        except Exception as e:
            logger.error(f"Error in video generation (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying...")
                await asyncio.sleep(2)
            else:
                logger.error(f"Failed after {max_retries} attempts")
                return None
        finally:
            try:
                if runware:
                    await runware.close()
            except:
                pass
    
    return None
