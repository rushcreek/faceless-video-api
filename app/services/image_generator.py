import re
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from app.services.image_api import fal_flux_api, replicate_flux_api, runware_flux_api, runware_flux_batch_api, runware_pocketrag_image_api
from app.core.config import settings
from app.core.logging import logger
from app.utils.helpers import create_blank_image
from app.models.image import Image
# from app.models.image_task import ImageTask
import asyncio
import time
from PIL import Image as PILImage
import os
import io
import requests

class ImageGenerator:
    def __init__(self, image_generator_func: Callable[[str], Optional[str]] = None):
        self.image_generator_func = image_generator_func
        self.assets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        self.prscreen_path = os.path.join(self.assets_path, "prscreen.png")
    
    def has_pocketrag_mention(self, text: str) -> bool:
        """Check if text mentions PocketRAG in any form"""
        text_lower = text.lower()
        pocketrag_variations = ['pocketrag', 'pocket rag', 'pocket-rag']
        return any(variation in text_lower for variation in pocketrag_variations)
    
    def prepare_prompt(
        self,
        storyboard: Dict[str, Any],
        characters: List[Dict[str, Any]],
        style: str,
        tweak_prompt: str = None
    ) -> str:
        """Prepare enhanced prompt without generating image"""
        # Construct the prompt
        prompt = storyboard['description']
        camera_info = f"Camera: {storyboard['camera']['angle']}, {storyboard['camera']['composition_type']}, {storyboard['camera']['shot_size']}"
        lighting_info = f"Lighting: {storyboard['lighting']}"
        
        enhanced_prompt = f"{prompt} | {style} | {camera_info} | {lighting_info}"
        
        # Check if PocketRAG is mentioned and add special instructions
        if self.has_pocketrag_mention(prompt):
            # Very explicit instruction that should override the scene description
            pocketrag_instruction = "IMPORTANT: Show a person's hands holding a modern iPhone (black or white), with the iPhone screen prominently displayed and clearly visible facing the camera. The iPhone screen must show the PocketRAG mobile app interface with clean modern UI elements, text, and controls visible on the screen. The phone should be the main focus of the image"
            enhanced_prompt = f"{pocketrag_instruction} | {enhanced_prompt}"
            logger.info(f"🎯 PocketRAG detected - adding iPhone display instruction")
        
        # Add tweak prompt if provided
        if tweak_prompt:
            enhanced_prompt += f" | {tweak_prompt}"
        
        # Add character descriptions
        character_descriptions = []
      
        for character in characters:
            name_forms = [
                character['name'].split()[0],  # First name
                character['name'],  # Full name
                f"{character['name'].split()[0]}'s",  # First name possessive
                f"{character['name']}'s",  # Full name possessive
                f"{character['name'].split()[0]}'",  # First name possessive (alternative)
                f"{character['name']}'",  # Full name possessive (alternative)
            ]
            
            # Check if any non-bracketed form of the name is in the prompt
            if any(
                form.lower() in prompt.lower() and 
                f"{{{{{form.lower()}}}}}" not in prompt.lower()
                for form in name_forms
            ):
                desc = f"{character['name']}'s appearance: {character['ethnicity']} {character['gender']} {character['age']} {character['facial_features']} {character['body_type']} {character['hair_style']} {character['accessories']}"
                character_descriptions.append(desc)

        if character_descriptions:
            enhanced_prompt += " | " + " | ".join(character_descriptions)
        
        # Remove all bracketed content
        enhanced_prompt = re.sub(r'\{\{.*?\}\}', '', enhanced_prompt)
        
        return enhanced_prompt 

    async def prepare_and_generate_image(
        self,
        task_id: str,
        storyboard: Dict[str, Any],
        characters: List[Dict[str, Any]],
        style: str,
        tweak_prompt: str = None
    ) -> Optional[str]:
        # Construct the prompt
        prompt = storyboard['description']
        camera_info = f"Camera: {storyboard['camera']['angle']}, {storyboard['camera']['composition_type']}, {storyboard['camera']['shot_size']}"
        lighting_info = f"Lighting: {storyboard['lighting']}"
        
        enhanced_prompt = f"{prompt} | {style} | {camera_info} | {lighting_info}"
        
        # Check if PocketRAG is mentioned and add special instructions
        if self.has_pocketrag_mention(prompt):
            # Very explicit instruction that should override the scene description
            pocketrag_instruction = "IMPORTANT: Show a person's hands holding a modern iPhone (black or white), with the iPhone screen prominently displayed and clearly visible facing the camera. The iPhone screen must show the PocketRAG mobile app interface with clean modern UI elements, text, and controls visible on the screen. The phone should be the main focus of the image"
            enhanced_prompt = f"{pocketrag_instruction} | {enhanced_prompt}"
            logger.info(f"🎯 PocketRAG detected in scene - adding iPhone display instruction")
        
        # Add tweak prompt if provided
        if tweak_prompt:
            enhanced_prompt += f" | {tweak_prompt}"
        
        # Add character descriptions
        character_descriptions = []
      
        for character in characters:
            name_forms = [
                character['name'].split()[0],  # First name
                character['name'],  # Full name
                f"{character['name'].split()[0]}'s",  # First name possessive
                f"{character['name']}'s",  # Full name possessive
                f"{character['name'].split()[0]}'",  # First name possessive (alternative)
                f"{character['name']}'"  # Full name possessive (alternative)
            ]
            
            # Check if any non-bracketed form of the name is in the prompt
            if any(
                form.lower() in prompt.lower() and 
                f"{{{{{form.lower()}}}}}" not in prompt.lower()
                for form in name_forms
            ):
                desc = f"{character['name']}'s appearance: {character['ethnicity']} {character['gender']} {character['age']} {character['facial_features']} {character['body_type']} {character['hair_style']} {character['accessories']}"
                character_descriptions.append(desc)

        if character_descriptions:
            enhanced_prompt += " | " + " | ".join(character_descriptions)
        
        # Remove all bracketed content
        enhanced_prompt = re.sub(r'\{\{.*?\}\}', '', enhanced_prompt)
        
        logger.debug(f"Enhanced prompt for task {task_id}: {enhanced_prompt}")

        image_url = await self.image_generator_func(task_id, enhanced_prompt)
        
        if image_url:
            logger.info(f"Image generated successfully for task {task_id}")
        else:
            logger.error(f"Failed to generate image for task {task_id}")

        return image_url, enhanced_prompt

    async def generate_images(self, task_id: str, storyboard_project: Dict[str, Any], art_style: str, tweak_prompt: str = None, progress_callback=None) -> List[str]:
        start_time = time.time()

        characters = storyboard_project.get('characters', [])
        total_images = len(storyboard_project['storyboards'])
        
        # Check if using Runware for parallel batch generation
        if settings.use_runware_flux:
            logger.info(f"🚀 Using Runware PARALLEL batch API for {total_images} images")
            
            # Separate PocketRAG scenes from regular scenes
            pocketrag_scenes = []
            regular_scenes = []
            enhanced_prompts = []
            
            for i, storyboard in enumerate(storyboard_project['storyboards']):
                enhanced_prompt = self.prepare_prompt(storyboard, characters, art_style, tweak_prompt)
                enhanced_prompts.append(enhanced_prompt)
                
                # Check if this scene mentions PocketRAG in description or subtitles
                description = storyboard.get('description', '')
                subtitles = storyboard.get('subtitles', '')
                if self.has_pocketrag_mention(description) or self.has_pocketrag_mention(subtitles):
                    pocketrag_scenes.append((i, enhanced_prompt))
                    logger.info(f"📱 Scene {i+1} identified as PocketRAG scene")
                else:
                    regular_scenes.append((i, enhanced_prompt))
                
                logger.debug(f"Prepared prompt for scene {storyboard.get('scene_number')}: {enhanced_prompt[:100]}...")
            
            # Generate regular images in parallel batch
            regular_prompts = [prompt for _, prompt in regular_scenes]
            regular_image_results = []
            if regular_prompts:
                logger.info(f"📸 Generating {len(regular_prompts)} regular images in parallel...")
                regular_image_results = await runware_flux_batch_api(task_id, regular_prompts)
            
            # Generate PocketRAG images individually with special model
            pocketrag_image_results = []
            if pocketrag_scenes:
                logger.info(f"📱 Generating {len(pocketrag_scenes)} PocketRAG images with Flux.2 [dev]...")
                for scene_idx, prompt in pocketrag_scenes:
                    result = await runware_pocketrag_image_api(task_id, prompt)
                    pocketrag_image_results.append(result)
            
            # Combine results in correct order
            image_results = [None] * total_images
            
            # Place regular images
            for i, (scene_idx, _) in enumerate(regular_scenes):
                if i < len(regular_image_results):
                    image_results[scene_idx] = regular_image_results[i]
            
            # Place PocketRAG images
            for i, (scene_idx, _) in enumerate(pocketrag_scenes):
                if i < len(pocketrag_image_results):
                    image_results[scene_idx] = pocketrag_image_results[i]
            
            # Process results and update progress
            for i, (image_result, enhanced_prompt) in enumerate(zip(image_results, enhanced_prompts)):
                if image_result and isinstance(image_result, dict):
                    image_url = image_result.get('url')
                    image_cost = image_result.get('cost')
                    
                    storyboard_project['storyboards'][i]['image'] = image_url
                    storyboard_project['storyboards'][i]['enhanced_prompt'] = enhanced_prompt
                    storyboard_project['storyboards'][i]['image_generation_cost'] = image_cost  # Store cost
                    storyboard_project['storyboards'][i]['error_message'] = None
                    
                    if image_cost is not None:
                        logger.info(f"✅ Image {i+1} generated successfully: {image_url} (cost: ${image_cost:.6f})")
                    else:
                        logger.info(f"✅ Image {i+1} generated successfully: {image_url}")
                else:
                    error_message = "Image generation failed: returned None"
                    logger.error(f"❌ Error generating image {i+1}")
                    storyboard_project['storyboards'][i]['image'] = None
                    storyboard_project['storyboards'][i]['enhanced_prompt'] = enhanced_prompt
                    storyboard_project['storyboards'][i]['image_generation_cost'] = None
                    storyboard_project['storyboards'][i]['error_message'] = error_message
                
                # Call progress callback after each image result is processed
                if progress_callback:
                    await progress_callback(i + 1, total_images)
            
            end_time = time.time()
            total_time = end_time - start_time
            successful = sum(1 for result in image_results if result and isinstance(result, dict) and result.get('url'))
            logger.info(f"🎉 Parallel generation completed: {successful}/{total_images} successful in {total_time:.2f}s")
            logger.info(f"⚡ Average time per image: {total_time/total_images:.2f}s")
            
            # Extract URLs for return (maintain backwards compatibility)
            image_urls = [
                result.get('url') if (result and isinstance(result, dict)) else None
                for result in image_results
            ]
            
            return image_urls
        
        # Fallback to sequential generation for Fal/Replicate
        else:
            logger.info(f"Using sequential generation for {total_images} images")
            tasks = []
            
            for i, storyboard in enumerate(storyboard_project['storyboards']):
                task = self.prepare_and_generate_image(task_id, storyboard, characters, art_style, tweak_prompt)
                tasks.append(task)

            # Process images with progress updates
            results = []
            for i, task_coro in enumerate(tasks):
                result = await task_coro
                results.append(result)
                
                # Call progress callback after each image completes
                if progress_callback:
                    await progress_callback(i + 1, total_images)
            
            image_urls = []
            for i, result in enumerate(results):
                if isinstance(result, tuple) and len(result) == 2:
                    image_url, enhanced_prompt = result
                    if image_url is not None:
                        storyboard_project['storyboards'][i]['image'] = image_url
                        storyboard_project['storyboards'][i]['enhanced_prompt'] = enhanced_prompt
                        storyboard_project['storyboards'][i]['error_message'] = None
                        image_urls.append(image_url)
                        logger.info(f"Image {i+1} generated successfully for task {task_id}: {image_url}")
                    else:
                        error_message = "Image generation failed: image_url is None"
                        logger.error(f"Error generating image {i+1} for task {task_id}: {error_message}")
                        storyboard_project['storyboards'][i]['image'] = None
                        storyboard_project['storyboards'][i]['enhanced_prompt'] = enhanced_prompt
                        storyboard_project['storyboards'][i]['error_message'] = error_message
                        image_urls.append(None)
                else:
                    if isinstance(result, Exception):
                        error_message = str(result)
                    else:
                        error_message = f"Unexpected result: {result}"
                    
                    logger.error(f"Error generating image {i+1} for task {task_id}: {error_message}")
                    storyboard_project['storyboards'][i]['image'] = None
                    storyboard_project['storyboards'][i]['enhanced_prompt'] = None
                    storyboard_project['storyboards'][i]['error_message'] = error_message
                    image_urls.append(None)

            end_time = time.time()
            total_time = end_time - start_time
            logger.info(f"generate_images completed for task {task_id} in {total_time:.2f} seconds")
            logger.info(f"Total images generated for task {task_id}: {len(image_urls)}")

            return image_urls

    async def regenerate_image(self, task_id: str, image_id: str) -> Optional[str]:
        image = await Image.get(image_id)
        if not image:
            logger.error(f"Image not found: {image_id}")
            return None

        image_url = await self.image_generator_func(task_id, image.enhanced_prompt)

        current_time = datetime.now()

        if image_url:
            # Append the new URL to the existing list of URLs
            urls = image.urls or []
            urls.append(image_url)
            await Image.update(image_id, urls=urls, status="completed", updated_at=current_time)
            logger.info(f"Image regenerated successfully for task {task_id}, image {image_id}")
        else:
            await Image.update(image_id, status="failed", updated_at=current_time)
            logger.error(f"Failed to regenerate image for task {task_id}, image {image_id}")

        # await ImageTask.update(task_id, updated_at=current_time)

        return image_url