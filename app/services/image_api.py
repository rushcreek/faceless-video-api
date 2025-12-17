import asyncio
import aiohttp
import replicate
import ssl
from typing import Optional
from app.core.config import settings
from app.core.logging import logger
import fal_client
from app.models.video_task import VideoTask  # Make sure this import is at the top of the file
from dotenv import load_dotenv
from runware import Runware, IImageInference


# just for loading API keys
load_dotenv()

async def replicate_flux_api(task_id: str, prompt: str, max_retries: int = 3) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            # Update task status to "processing"
            await VideoTask.update(task_id, status="processing")

            payload = {
                "prompt": prompt,
                "aspect_ratio": settings.replicate_flux_api.get('aspect_ratio'),
                "num_inference_steps": settings.replicate_flux_api.get('num_inference_steps'),
                "guidance": settings.replicate_flux_api.get('guidance'),
                "output_quality": settings.replicate_flux_api.get('output_quality'),
            }

            image_urls = replicate.run(
                settings.replicate_flux_api.get('model'),
                input=payload
            )

            if image_urls and isinstance(image_urls, list) and len(image_urls) > 0:
                image_url = image_urls[0]
                # Update task status to "completed" and save the image URL
                await VideoTask.update(task_id, status="completed", image_url=image_url)
                return image_url
            else:
                raise ValueError("No image URL returned from Replicate API")

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error in replicate_flux_api (attempt {attempt + 1}/{max_retries}): {str(e)}")
                logger.info("Retrying...")
                await asyncio.sleep(1)  # Wait for 1 second before retrying
            else:
                logger.error(f"Error in replicate_flux_api after {max_retries} attempts: {str(e)}")
                # Update task status to "failed" if all attempts fail
                await VideoTask.update(task_id, status="failed", error_message=str(e))
                raise

    return None


async def runware_flux_api(task_id: str, prompt: str, max_retries: int = 3) -> Optional[str]:
    """Generate image using Runware.ai Flux model"""
    
    for attempt in range(max_retries):
        runware = None
        try:
            # Initialize Runware client
            runware = Runware(api_key=settings.RUNWARE_API_KEY)
            await runware.connect()
            
            logger.info(f"Runware connected for task {task_id}, generating image...")
            
            # Prepare the request
            request_image = IImageInference(
                positivePrompt=prompt,
                model=settings.runware_flux_api.get('model'),
                width=settings.runware_flux_api.get('width'),
                height=settings.runware_flux_api.get('height'),
                numberResults=1,
                steps=settings.runware_flux_api.get('steps'),
                outputFormat="JPG",
                uploadEndpoint="runway"
            )
            
            # Generate image
            images = await runware.imageInference(requestImage=request_image)
            
            logger.info(f"Runware response for task {task_id}: {type(images)}, length: {len(images) if images else 0}")
            
            if images and len(images) > 0:
                # Check different possible attributes
                image_url = None
                if hasattr(images[0], 'imageURL'):
                    image_url = images[0].imageURL
                elif hasattr(images[0], 'image_url'):
                    image_url = images[0].image_url
                elif hasattr(images[0], 'url'):
                    image_url = images[0].url
                elif isinstance(images[0], dict):
                    image_url = images[0].get('imageURL') or images[0].get('image_url') or images[0].get('url')
                
                logger.info(f"Runware extracted URL for task {task_id}: {image_url}")
                
                if image_url:
                    logger.info(f"Runware API generated image for task {task_id}: {image_url}")
                    return image_url
                else:
                    logger.error(f"Image object attributes: {dir(images[0])}")
                    raise ValueError(f"Could not extract image URL from Runware response. Response: {images[0]}")
            else:
                raise ValueError("No images returned from Runware API")
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error in runware_flux_api (attempt {attempt + 1}/{max_retries}): {str(e)}")
                logger.info("Retrying...")
                await asyncio.sleep(2)
            else:
                logger.error(f"Error in runware_flux_api after {max_retries} attempts: {str(e)}")
                raise
        finally:
            try:
                if runware:
                    await runware.close()
            except Exception as close_error:
                logger.warning(f"Error closing Runware connection: {close_error}")
    
    return None


async def fal_flux_api(task_id: str, prompt: str, max_retries: int = 3) -> Optional[str]:

    for attempt in range(max_retries):
        try:
            # Submit the task to fal.ai
            if settings.use_fal_flux_dev:
                handler = await fal_client.submit_async(
                    settings.fal_flux_dev_api.get('model'),
                    arguments={
                        "prompt": prompt,
                        "image_size": settings.fal_flux_dev_api.get('image_size'),
                        "num_inference_steps": settings.fal_flux_dev_api.get('num_inference_steps'),
                        "guidance_scale": settings.fal_flux_dev_api.get('guidance_scale'),
                        "enable_safety_checker": settings.fal_flux_dev_api.get('enable_safety_checker'),
                        "num_images": settings.fal_flux_dev_api.get('num_images')
                    },
                )
            else:
                handler = await fal_client.submit_async(
                    settings.fal_flux_schnell_api.get('model'),
                    arguments={
                        "prompt": prompt,
                        "image_size": settings.fal_flux_schnell_api.get('image_size'),
                        "guidance_scale": settings.fal_flux_schnell_api.get('guidance_scale'),
                        "enable_safety_checker": settings.fal_flux_schnell_api.get('enable_safety_checker'),
                        "num_images": settings.fal_flux_schnell_api.get('num_images')
                    },
                )

            # Get the final result
            result = await handler.get()
            
            # Update task with the result
            image_urls = [image['url'] for image in result.get('images', [])]

            return image_urls[0]

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error in fal_flux_api (attempt {attempt + 1}/{max_retries}): {str(e)}")
                logger.info("Retrying...")
                await asyncio.sleep(1)  # Wait for 1 second before retrying
            else:
                logger.error(f"Error in fal_flux_api after {max_retries} attempts: {str(e)}")
                # Update task status to "failed" if all attempts fail
                await VideoTask.update(task_id, status="failed", error_message=str(e))
                raise

    return None
