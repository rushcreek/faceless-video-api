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
from runware.types import IInputs


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


async def runware_pocketrag_image_api(task_id: str, prompt: str, reference_image_url: str, max_retries: int = 3) -> Optional[dict]:
    """Generate image for PocketRAG scenes using Flux.2 [dev] model with reference image
    Returns dict with format: {"url": image_url, "cost": cost}
    """
    POCKETRAG_MODEL = "runware:400@1"  # Flux.2 [dev]
    for attempt in range(max_retries):
        runware = None
        try:
            # Initialize Runware client
            runware = Runware(api_key=settings.RUNWARE_API_KEY)
            await runware.connect()
            logger.info(f"📱 Generating PocketRAG image with Flux.2 [dev] model for task {task_id}...")
            logger.info(f"📱 Using reference image: {reference_image_url}")
            # Validate and truncate prompt if needed (Runware limit: 2-3000 chars)
            if not isinstance(prompt, str):
                logger.error(f"❌ Prompt is not a string: {type(prompt)}")
                return None
            
            if len(prompt) > 3000:
                logger.warning(f"⚠️ Prompt too long ({len(prompt)} chars), truncating to 3000")
                prompt = prompt[:3000]
            elif len(prompt) < 2:
                logger.error(f"❌ Prompt too short ({len(prompt)} chars), minimum is 2")
                return None
            
            logger.info(f"📝 Prompt length: {len(prompt)} characters")
            
            # Create request with Flux.2 [dev] model and reference image
            # referenceImages is passed directly to IImageInference, not through IInputs
            request_image = IImageInference(
                positivePrompt=prompt,
                model=POCKETRAG_MODEL,
                width=576,
                height=1024,
                numberResults=1,
                steps=28,
                outputFormat="JPG",
                CFGScale=3.5,
                scheduler="FlowMatchEulerDiscreteScheduler",
                includeCost=True,
                referenceImages=[reference_image_url],
                outputType=["URL"]
            )
            
            images = await runware.imageInference(requestImage=request_image)
            
            if images and len(images) > 0:
                logger.debug(f"📊 PocketRAG image response: {images[0]}")
                
                # Extract URL
                image_url = None
                if hasattr(images[0], 'imageURL'):
                    image_url = images[0].imageURL
                elif hasattr(images[0], 'image_url'):
                    image_url = images[0].image_url
                elif hasattr(images[0], 'url'):
                    image_url = images[0].url
                elif isinstance(images[0], dict):
                    image_url = images[0].get('imageURL') or images[0].get('image_url') or images[0].get('url')
                
                # Extract cost
                cost = None
                if hasattr(images[0], 'cost'):
                    cost = images[0].cost
                elif hasattr(images[0], 'credits'):
                    cost = images[0].credits
                elif isinstance(images[0], dict):
                    cost = images[0].get('cost') or images[0].get('credits')
                
                if cost is not None:
                    logger.info(f"💰 PocketRAG image cost: ${cost:.6f}")
                
                if image_url:
                    logger.info(f"✅ PocketRAG image generated successfully: {image_url}")
                    return {"url": image_url, "cost": cost}
                else:
                    logger.error(f"❌ Could not extract URL from PocketRAG image response")
                    return None
            else:
                logger.error(f"❌ No images returned for PocketRAG generation")
                return None
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error in runware_pocketrag_image_api (attempt {attempt + 1}/{max_retries}): {str(e)}")
                logger.info("Retrying...")
                await asyncio.sleep(2)
            else:
                logger.error(f"Error in runware_pocketrag_image_api after {max_retries} attempts: {str(e)}")
                return None
        finally:
            if runware:
                try:
                    await runware.close()
                except Exception as close_error:
                    logger.warning(f"Error closing Runware connection: {close_error}")
    
    return None


async def runware_flux_api(task_id: str, prompt: str, max_retries: int = 3) -> Optional[dict]:
    """Generate a single image using Runware.ai Flux model (kept for compatibility)"""
    results = await runware_flux_batch_api(task_id, [prompt], max_retries)
    return results[0] if results and len(results) > 0 else None


async def runware_flux_batch_api(task_id: str, prompts: list[str], max_retries: int = 3) -> list[Optional[dict]]:
    """Generate multiple images in parallel using Runware.ai Flux model with async streaming
    Returns list of dicts with format: {"url": image_url, "cost": cost}
    """
    
    for attempt in range(max_retries):
        runware = None
        try:
            # Initialize Runware client
            runware = Runware(api_key=settings.RUNWARE_API_KEY)
            await runware.connect()
            
            logger.info(f"🚀 Runware connected for task {task_id}, starting PARALLEL generation of {len(prompts)} images...")
            
            async def generate_single(prompt: str, index: int) -> Optional[dict]:
                """Generate a single image and return URL and cost"""
                try:
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
                    
                    images = await runware.imageInference(requestImage=request_image)
                    
                    if images and len(images) > 0:
                        # Log full response to discover cost fields
                        logger.debug(f"📊 Full Runware image response for image {index+1}: {images[0]}")
                        if hasattr(images[0], '__dict__'):
                            logger.debug(f"📊 Response attributes: {images[0].__dict__}")
                        
                        # Extract URL from response
                        image_url = None
                        if hasattr(images[0], 'imageURL'):
                            image_url = images[0].imageURL
                        elif hasattr(images[0], 'image_url'):
                            image_url = images[0].image_url
                        elif hasattr(images[0], 'url'):
                            image_url = images[0].url
                        elif isinstance(images[0], dict):
                            image_url = images[0].get('imageURL') or images[0].get('image_url') or images[0].get('url')
                        
                        # Extract cost from response (similar to video SDK)
                        cost = None
                        if hasattr(images[0], 'cost'):
                            cost = images[0].cost
                        elif hasattr(images[0], 'credits'):
                            cost = images[0].credits
                        elif isinstance(images[0], dict):
                            cost = images[0].get('cost') or images[0].get('credits')
                        
                        if cost is not None:
                            logger.info(f"💰 Image {index+1} cost: ${cost:.6f}")
                        
                        if image_url:
                            logger.info(f"✅ Parallel image {index+1}/{len(prompts)} completed: {image_url}")
                            return {"url": image_url, "cost": cost}
                        else:
                            logger.error(f"❌ Could not extract URL from image {index+1}")
                            return None
                    else:
                        logger.error(f"❌ No images returned for prompt {index+1}")
                        return None
                        
                except Exception as e:
                    logger.error(f"❌ Error generating parallel image {index+1}: {str(e)}")
                    return None
            
            # Generate ALL images in parallel using asyncio.gather
            import time
            start_time = time.time()
            
            results = await asyncio.gather(
                *[generate_single(prompt, i) for i, prompt in enumerate(prompts)],
                return_exceptions=True
            )
            
            # Convert exceptions to None
            image_results = [
                result if not isinstance(result, Exception) else None 
                for result in results
            ]
            
            elapsed = time.time() - start_time
            successful = sum(1 for result in image_results if result)
            logger.info(f"✅ Parallel generation complete: {successful}/{len(prompts)} successful in {elapsed:.2f}s")
            
            return image_results
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error in runware_flux_batch_api (attempt {attempt + 1}/{max_retries}): {str(e)}")
                logger.info("Retrying...")
                await asyncio.sleep(2)
            else:
                logger.error(f"Error in runware_flux_batch_api after {max_retries} attempts: {str(e)}")
                # Return list of None for all prompts on complete failure
                return [None] * len(prompts)
        finally:
            try:
                if runware:
                    await runware.close()
            except Exception as close_error:
                logger.warning(f"Error closing Runware connection: {close_error}")
    
    return [None] * len(prompts)


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
