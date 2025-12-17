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
from app.services.image_api import fal_flux_api, replicate_flux_api, runware_flux_api
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
        if settings.use_runware_flux:
            image_gen_func = runware_flux_api
        elif settings.use_fal_flux:
            image_gen_func = fal_flux_api
        else:
            image_gen_func = replicate_flux_api
        self.image_generator = ImageGenerator(image_generator_func=image_gen_func)
        self.video_generator = VideoGenerator(self.client)
        self.storage_service = StorageService()

    async def process_video_generation_task(self, task_id: str, art_style: str, duration: str, language: str, voice_name: str, custom_story: str, custom_title: str = None, story_style_descriptor: str = None, caption_font: str = 'BebasNeue', tweak_prompt: str = None):
        task = await VideoTask.get(task_id)
        # Progress tracking based on actual timing (total ~2-3 minutes):
        # 0-5%: Story setup (~3s)
        # 5-15%: Characters generation (~10s)
        # 15-30%: Storyboard generation (~30s)
        # 30-45%: Image generation (~15s with parallel Runware)
        # 45-50%: Save images to database (~3s)
        # 50-100%: Video generation and upload (~60-90s - SLOWEST phase)

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
            
            await task.update(task_id=task_id, progress=0.05, status_message="Story prepared")

            # Step 2: Create resource directory and generate characters
            story_dir_name = story_style_descriptor if story_style_descriptor else "custom"
            story_dir = create_resource_dir(settings.STORY_DIR, story_dir_name, title)
            
            # Only generate characters for narrative stories
            characters = []
            if story_style_descriptor in ['dramatic', 'mysterious', 'epic', 'intimate']:
                characters = await self.story_generator.generate_characters(story)
            
            await task.update(task_id=task_id, progress=0.15, status_message="Characters created")

            # Step 3: Generate storyboard
            storyboard_project = await self.story_generator.generate_storyboard(
                title, 
                story, 
                [c["name"] for c in characters],
                tweak_prompt=tweak_prompt,
                art_style=art_style
            )
            if not storyboard_project.get("storyboards"):
                raise ValueError("Failed to generate storyboard")
            storyboard_project["characters"] = characters
            await task.update(task_id=task_id, progress=0.30, status_message="Storyboard created")

            # Step 4: Generate images with combined art style + descriptor
            combined_art_style = art_style
            if story_style_descriptor:
                combined_art_style = f"{story_style_descriptor} {art_style}"
            
            # Progress callback for image generation (30% to 45% = 15% total)
            total_images = len(storyboard_project.get("storyboards", []))
            async def image_progress_callback(completed, total):
                # Map image progress from 30% to 45%
                progress = 0.30 + (0.15 * (completed / total))
                await task.update(task_id=task_id, progress=round(progress, 2), status_message=f"Generating images ({completed}/{total})")
            
            image_urls = await self.image_generator.generate_images(task_id, storyboard_project, combined_art_style, tweak_prompt, progress_callback=image_progress_callback)
            if not image_urls:
                raise ValueError("Failed to generate images")
            await task.update(task_id=task_id, progress=0.45, status_message="Images generated")

            # Step 5: Save images to database
            image_create_tasks = []
            for i, image_url in enumerate(image_urls):
                storyboard_scene = storyboard_project["storyboards"][i]
                image_data = {
                    "id": str(uuid4()),
                    "task_id": task_id,
                    "urls": [image_url] if image_url else [],
                    "subtitles": storyboard_scene["description"],
                    "status": "completed" if image_url else "failed",
                    "enhanced_prompt": storyboard_scene.get("enhanced_prompt", ""),
                    "video_generation_request": storyboard_scene.get("video_generation_request"),
                    "error_message": storyboard_scene.get("error_message", "")
                }
                image_create_tasks.append(Image.create(**image_data))
            await asyncio.gather(*image_create_tasks)
            await task.update(task_id=task_id, progress=0.50, status_message="Images saved")

            # Step 6: Generate and upload video
            # Progress callback for video generation (50% to 98%)
            async def video_progress_callback(progress_value, message):
                # Map internal video progress (0.90-0.98) to overall progress (50-98%)
                # Internal: 0.91 -> 54%, 0.915 -> 62%, 0.918 -> 68%, 0.92 -> 70%, 0.96 -> 90%, 0.98 -> 98%
                if progress_value <= 0.91:
                    overall_progress = 0.50 + (progress_value - 0.90) * 40  # 0.90-0.91 -> 50-54%
                elif progress_value <= 0.915:
                    overall_progress = 0.54 + (progress_value - 0.91) * 160  # 0.91-0.915 -> 54-62%
                elif progress_value <= 0.918:
                    overall_progress = 0.62 + (progress_value - 0.915) * 200  # 0.915-0.918 -> 62-68%
                elif progress_value <= 0.92:
                    overall_progress = 0.68 + (progress_value - 0.918) * 100  # 0.918-0.92 -> 68-70%
                elif progress_value <= 0.96:
                    overall_progress = 0.70 + (progress_value - 0.92) * 5  # 0.92-0.96 -> 70-90%
                else:
                    overall_progress = 0.90 + (progress_value - 0.96) * 4  # 0.96-0.98 -> 90-98%
                await task.update(task_id=task_id, progress=round(overall_progress, 2), status_message=message)
            
            video_path = await self.video_generator.generate_video(
                storyboard_project, 
                story_dir, 
                voice_name, 
                caption_font,
                progress_callback=video_progress_callback
            )
            if not video_path:
                raise ValueError("Failed to create video")

            # Get the last directory name from story_dir
            await task.update(task_id=task_id, progress=0.98, status_message="Uploading video...")
            video_name = os.path.basename(os.path.normpath(story_dir))
            object_name = f"videos/{task_id}/{video_name}.mp4"
            r2_url = await self.storage_service.upload_to_r2(video_path, object_name)
            logger.info(f"Video uploaded to R2: {r2_url}")
            if not r2_url:
                raise ValueError("Failed to upload video to R2")

            # Use public R2 URL format
            public_url = f"https://pub-b9f9db5f1fcd4c7fa65abaa742ab9de0.r2.dev/{object_name}"
            
            # Update the video_task table instead of creating a new video record
            update_data = {
                "url": public_url,
                "story_title": title,
                "story_description": description,
                "story_text": story,
                "status": "completed"
            }
            updated_task = await task.update(task_id=task_id, **update_data)
            if not updated_task:
                raise ValueError("Failed to update video task record in database")

            await task.update(task_id=task_id, status="completed", progress=1.0, status_message="Video ready!")
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
