import os
from uuid import uuid4
from openai import AsyncAzureOpenAI, AsyncOpenAI
from app.core.config import settings
from app.services.story_generator import StoryGenerator
from app.models.image import Image
from app.services.image_generator import ImageGenerator
from app.services.video_generator import VideoGenerator 
from app.utils.helpers import create_resource_dir
from app.models.video_task import VideoTask
from app.constants.story_types import STORY_STYLE_DESCRIPTORS
from app.services.image_api import fal_flux_api, replicate_flux_api
from app.core.logging import logger
from app.services.storage import StorageService
import asyncio
import shutil

class VideoTaskProcessor:
    def __init__(self):
        if settings.use_azure_openai:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.azure_api_version
            )
        else:
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
        self.story_generator = StoryGenerator(self.client)

        # Choose the image generation function based on configuration
        image_gen_func = fal_flux_api if settings.use_fal_flux else replicate_flux_api
        self.image_generator = ImageGenerator(image_generator_func=image_gen_func)
        self.video_generator = VideoGenerator(self.client)
        self.storage_service = StorageService()

    async def process_video_generation_task(self, task_id: str, art_style: str, duration: str, language: str, voice_name: str, custom_story: str, custom_title: str = None, story_style_descriptor: str = None):
        task = await VideoTask.get(task_id)
        total_steps = 6  # Total number of main steps in the process
        completed_steps = 0

        try:
            await task.update(task_id=task_id, status="processing", progress=0)

            # Step 1: Use custom story (now required)
            story = custom_story
            title = custom_title if custom_title else "Custom Story"
            description = f"A custom video story #facelessvideos.app"
            
            # Add style descriptor to description if provided
            if story_style_descriptor:
                description = f"A {story_style_descriptor} video story #facelessvideos.app"
            
            logger.info(f"Processing task {task_id} with story_style_descriptor: {story_style_descriptor}")
            
            completed_steps += 1
            await task.update(task_id=task_id, progress=round(completed_steps/total_steps, 1))

            # Step 2: Create resource directory and generate characters
            story_dir_name = story_style_descriptor if story_style_descriptor else "custom"
            story_dir = create_resource_dir(settings.STORY_DIR, story_dir_name, title)
            
            # Only generate characters for narrative stories
            characters = []
            if story_style_descriptor in ['dramatic', 'mysterious', 'epic', 'intimate']:
                characters = await self.story_generator.generate_characters(story)
            
            completed_steps += 1
            await task.update(task_id=task_id, progress=round(completed_steps/total_steps, 1))

            # Step 3: Generate storyboard
            # Combine style descriptor with story for better image prompts
            enhanced_story = story
            if story_style_descriptor:
                enhanced_story = f"[{story_style_descriptor.upper()} MOOD] {story}"
            
            storyboard_project = await self.story_generator.generate_storyboard(story_dir_name, title, enhanced_story, [c["name"] for c in characters])
            if not storyboard_project.get("storyboards"):
                raise ValueError("Failed to generate storyboard")
            storyboard_project["characters"] = characters
            completed_steps += 1
            await task.update(task_id=task_id, progress=round(completed_steps/total_steps, 1))

            # Step 4: Generate images with combined art style + descriptor
            combined_art_style = art_style
            if story_style_descriptor:
                combined_art_style = f"{story_style_descriptor} {art_style}"
            
            image_urls = await self.image_generator.generate_images(task_id, storyboard_project, combined_art_style)
            if not image_urls:
                raise ValueError("Failed to generate images")
            completed_steps += 1
            await task.update(task_id=task_id, progress=round(completed_steps/total_steps, 1))

            # Step 5: Save images to database
            image_create_tasks = []
            for i, image_url in enumerate(image_urls):
                image_data = {
                    "id": str(uuid4()),
                    "task_id": task_id,
                    "urls": [image_url] if image_url else [],
                    "subtitles": storyboard_project["storyboards"][i]["description"],
                    "status": "completed" if image_url else "failed",
                    "enhanced_prompt": storyboard_project["storyboards"][i].get("enhanced_prompt", ""),
                    "error_message": storyboard_project["storyboards"][i].get("error_message", "")
                }
                image_create_tasks.append(Image.create(**image_data))
            await asyncio.gather(*image_create_tasks)
            completed_steps += 1
            await task.update(task_id=task_id, progress=round(completed_steps/total_steps, 1))

            # Step 6: Generate and upload video
            video_path = await self.video_generator.generate_video(storyboard_project, story_dir, voice_name)
            if not video_path:
                raise ValueError("Failed to create video")

            # Get the last directory name from story_dir
            video_name = os.path.basename(os.path.normpath(story_dir))
            object_name = f"videos/{task_id}/{video_name}.mp4"
            r2_url = await self.storage_service.upload_to_r2(video_path, object_name)
            logger.info(f"Video uploaded to R2: {r2_url}")
            if not r2_url:
                raise ValueError("Failed to upload video to R2")

            # Update the video_task table instead of creating a new video record
            update_data = {
                "url": r2_url,
                "story_title": title,
                "story_description": description,
                "story_text": story,
                "status": "completed"
            }
            updated_task = await task.update(task_id=task_id, **update_data)
            if not updated_task:
                raise ValueError("Failed to update video task record in database")

            completed_steps += 1
            await task.update(task_id=task_id, status="completed", progress=round(completed_steps/total_steps, 1))
        except Exception as e:
            logger.error(f"Error in video generation task: {str(e)}")
            await task.update(task_id=task_id, status="failed", error_message=str(e))
        finally:
            pass
            # TODO: Cleanup temporary files
            # if 'video_path' in locals() and os.path.exists(video_path):
            #     os.remove(video_path)
            # if 'story_dir' in locals() and os.path.exists(story_dir):
            #     shutil.rmtree(story_dir)
