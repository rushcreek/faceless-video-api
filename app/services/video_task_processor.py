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
                api_version=settings.azure_api_version,
                timeout=120.0,  # 2 minute timeout for API calls
                max_retries=3   # Retry failed requests up to 3 times
            )
        else:
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                timeout=120.0,  # 2 minute timeout for API calls
                max_retries=3   # Retry failed requests up to 3 times
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
            description = f"A custom video story #danwegner.com"
            
            # Add style descriptor to description if provided
            if story_style_descriptor:
                description = f"A {story_style_descriptor} video story #danwegner.com"
            
            logger.info(f"Processing task {task_id} with story_style_descriptor: {story_style_descriptor}")
            
            # Save title and description to database
            await task.update(
                task_id=task_id, 
                progress=0.05, 
                status_message="Story prepared",
                story_title=title,
                story_description=description,
                story_text=story
            )

            # Step 2: Create resource directory and generate characters
            story_dir_name = story_style_descriptor if story_style_descriptor else "custom"
            story_dir = create_resource_dir(settings.STORY_DIR, story_dir_name, title)
            
            # Only generate characters for narrative stories
            characters = []
            if story_style_descriptor in ['dramatic', 'mysterious', 'epic', 'intimate']:
                characters = await self.story_generator.generate_characters(story)
            
            await task.update(task_id=task_id, progress=0.15, status_message="Characters created")

            # Check if task was cancelled
            task = await VideoTask.get(task_id)
            if task.status == "failed":
                logger.info(f"Task {task_id} was cancelled, stopping processing")
                return

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

            # Step 4: (Image generation moved to video_generator.py after caption timing/phrases are known)
            await task.update(task_id=task_id, progress=0.45, status_message="Ready for video generation (images will be generated after captions)")

            # Step 5: Save images to database
            image_create_tasks = []
            for i, image_url in enumerate(image_urls):
                storyboard_scene = storyboard_project["storyboards"][i]
                scene_number = storyboard_scene.get("scene_number", i + 1)
                
                logger.info(f"💾 Saving scene {scene_number} to database: URL={'Present' if image_url else 'MISSING'}")
                if not image_url:
                    logger.error(f"❌ Scene {scene_number} has NO IMAGE URL - will be saved as empty")
                
                image_data = {
                    "id": str(uuid4()),
                    "task_id": task_id,
                    "scene_number": scene_number,  # Preserve scene order from storyboard
                    "urls": [image_url] if image_url else [],
                    "subtitles": storyboard_scene["subtitles"],  # Use actual subtitles from storyboard, not description
                    "status": "completed" if image_url else "failed",
                    "enhanced_prompt": storyboard_scene.get("enhanced_prompt", ""),
                    "video_generation_request": storyboard_scene.get("video_generation_request"),
                    "audio_duration": storyboard_scene.get("audio_duration"),  # Store scene duration from audio
                    "image_generation_cost": storyboard_scene.get("image_generation_cost"),  # Store image generation cost
                    "error_message": storyboard_scene.get("error_message", "")
                }
                image_create_tasks.append(Image.create(**image_data))
            
            logger.info(f"💾 Saving {len(image_create_tasks)} image records to database...")
            await asyncio.gather(*image_create_tasks)
            logger.info(f"✅ All {len(image_create_tasks)} image records saved to database")
            
            # Verify what was actually saved
            saved_images = await Image.list_by_task(task_id)
            logger.info(f"🔍 Verification: Found {len(saved_images)} images in database for task {task_id}")
            
            # Check for any failed images and fatal error if found
            failed_images = []
            for img in saved_images:
                url_status = f"URL: {img.urls[0][:80]}..." if img.urls else "NO URLs"
                logger.info(f"  Scene {img.scene_number}: {img.status} - {url_status}")
                
                if img.status == "failed" or not img.urls:
                    failed_images.append(f"Scene {img.scene_number}")
            
            if failed_images:
                error_msg = f"Image generation failed for {len(failed_images)} scene(s): {', '.join(failed_images)}. Cannot proceed with video generation."
                logger.error(f"❌ FATAL: {error_msg}")
                await task.update(task_id=task_id, status="failed", error_message=error_msg)
                raise ValueError(error_msg)
            
            await task.update(task_id=task_id, progress=0.50, status_message="Images saved")

            # Check if task was cancelled
            task = await VideoTask.get(task_id)
            if task.status == "failed":
                logger.info(f"Task {task_id} was cancelled, stopping before audio generation")
                return

            # Step 5.5: Generate audio files and update durations in database
            await task.update(
                task_id=task_id,
                progress=0.50,
                status_message="Generating audio for scenes..."
            )
            
            try:
                await self.generate_audio_for_scenes(task_id, voice_name)
                logger.info(f"✅ Audio generation and duration update completed for task {task_id}")
            except Exception as e:
                logger.error(f"❌ Failed to generate audio: {str(e)}", exc_info=True)
                # Continue without audio - finalization will regenerate if needed
                logger.warning(f"Continuing task {task_id} - audio will be regenerated during finalization")

            # Check if task was cancelled
            task = await VideoTask.get(task_id)
            if task.status == "failed":
                logger.info(f"Task {task_id} was cancelled after audio generation")
                return

            # Step 5.6: Generate video clips automatically for first, last, and one middle scene
            await task.update(
                task_id=task_id, 
                status="processing", 
                progress=0.52, 
                status_message="Generating video clips for key scenes..."
            )
            
            # Import and call video clip generation with smart scene selection
            from app.api.endpoints.video_clips import process_video_clips_background_with_durations
            try:
                logger.info(f"⚡ About to call process_video_clips_background_with_durations for task {task_id}")
                await process_video_clips_background_with_durations(task_id)
                logger.info(f"✅ Video clips generation function completed for task {task_id}")
            except Exception as e:
                logger.error(f"❌ EXCEPTION in video clip generation: {str(e)}", exc_info=True)
                # DON'T fail the whole task - continue without video clips
                logger.warning(f"Continuing task {task_id} without video clips due to error")
            
            # Check if task was cancelled during video clip generation
            task = await VideoTask.get(task_id)
            if task.status == "failed":
                logger.info(f"Task {task_id} was cancelled during video clip generation")
                return
            
            # Step 5.7: Automatically finalize the video
            await task.update(
                task_id=task_id,
                progress=0.55,
                status_message="Finalizing video with clips and images..."
            )
            
            try:
                await self.finalize_video_with_clips(task_id)
                logger.info(f"Video finalized successfully for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to finalize video: {str(e)}")
                await task.update(
                    task_id=task_id,
                    status="failed",
                    error_message=f"Finalization failed: {str(e)}"
                )
                return
            
            # Finalization complete - task should now be marked as completed
            logger.info(f"Task {task_id} completed successfully")
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

    async def generate_audio_for_scenes(self, task_id: str, voice_name: str):
        """
        Generate audio files for all scenes and update their durations in the database.
        This should be called BEFORE video clip generation so clips have correct durations.
        Audio files are saved to the task's story directory for reuse during finalization.
        """
        from app.services.audio_generator import AudioGenerator
        from moviepy.editor import AudioFileClip
        
        # Get task to determine story directory
        task = await VideoTask.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        # Get all images for this task
        images = await Image.list_by_task(task_id)
        if not images:
            logger.warning(f"No images found for task {task_id}")
            return
        
        # Sort by scene number
        images.sort(key=lambda x: x.scene_number or 0)
        
        # Create story directory to store audio files
        from app.utils.helpers import create_resource_dir
        story_dir_name = task.story_style_descriptor or "custom"
        story_dir = create_resource_dir(settings.STORY_DIR, story_dir_name, task.custom_title or "Video")
        audio_dir = os.path.join(story_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        audio_generator = AudioGenerator()
        
        for image in images:
            if not image.subtitles:
                logger.warning(f"No subtitles for scene {image.scene_number}, skipping audio generation")
                continue
            
            # Generate audio file to permanent location
            audio_file = os.path.join(audio_dir, f"scene_{image.scene_number}.mp3")
            
            logger.info(f"Generating audio for scene {image.scene_number}: {image.subtitles[:50]}...")
            await audio_generator.generate_audio(
                text=image.subtitles,
                output_file=audio_file,
                voice_name=voice_name
            )
            
            # Get duration from audio file
            if os.path.exists(audio_file):
                audio_clip = AudioFileClip(audio_file)
                duration = audio_clip.duration
                audio_clip.close()
                
                # Update database with duration
                await Image.update_by_task_and_scene(
                    task_id=task_id,
                    scene_number=image.scene_number,
                    audio_duration=duration
                )
                logger.info(f"✅ Scene {image.scene_number}: audio duration {duration:.2f}s saved to database")
            else:
                logger.error(f"Audio file not created for scene {image.scene_number}")

    async def finalize_video_with_clips(self, task_id: str):
        """
        Finalize the video by stitching together video clips and static images.
        This should be called AFTER video clips have been generated.
        """
        task = await VideoTask.get(task_id)
        
        try:
            await task.update(task_id=task_id, status="processing", progress=0.55, status_message="Preparing to finalize video...")
            
            # Get all images/scenes for this task
            images = await Image.list_by_task(task_id)
            if not images:
                raise ValueError("No scenes found for this task")
            
            # CRITICAL: Sort images to maintain storyboard narrative order
            # First try scene_number (new tasks), fall back to created_at (old tasks)
            def sort_key(img):
                if img.scene_number is not None:
                    return (0, img.scene_number)  # Priority 0 = use scene_number
                else:
                    return (1, img.created_at.timestamp())  # Priority 1 = use created_at as fallback
            
            images.sort(key=sort_key)
            logger.info(f"Sorted {len(images)} images to maintain narrative order")
            
            # Recreate the storyboard structure needed for video generation
            # This includes using video clips where available
            storyboard_project = {
                "project_info": {
                    "title": task.custom_title or "Custom Story",
                    "timestamp": task.created_at.strftime("%Y-%m-%d %I:%M:%S %p")
                },
                "storyboards": [],
                "characters": []  # Not needed for finalization
            }
            
            for idx, image in enumerate(images):
                scene = {
                    "scene_number": idx + 1,  # Add 1-based scene number for audio file naming
                    "subtitles": image.subtitles or "",
                    "description": image.subtitles or "",
                    "enhanced_prompt": image.enhanced_prompt or "",
                    "video_generation_request": image.video_generation_request,
                    "video_clip_url": image.video_clip_url,  # Use video clip if available
                    "image": image.urls[0] if image.urls else None,  # video_generator expects 'image'
                    "image_url": image.urls[0] if image.urls else None,
                    "urls": image.urls  # Keep original urls array for compatibility
                }
                storyboard_project["storyboards"].append(scene)
            
            # Create story directory
            from app.utils.helpers import create_resource_dir
            story_dir_name = task.story_style_descriptor or "custom"
            story_dir = create_resource_dir(settings.STORY_DIR, story_dir_name, task.custom_title or "Video")
            
            # Progress callback
            async def video_progress_callback(progress_value, message):
                await task.update(task_id=task_id, progress=round(progress_value, 2), status_message=message)
            
            # Generate final video (will use video clips where available)
            video_path = await self.video_generator.generate_video(
                storyboard_project,
                story_dir,
                task.voice_name,
                task.caption_font or 'BebasNeue',
                progress_callback=video_progress_callback,
                task_id=task_id
            )
            
            if not video_path:
                raise ValueError("Failed to create final video")
            
            # Upload to R2
            await task.update(task_id=task_id, progress=0.98, status_message="Uploading video...")
            video_name = os.path.basename(os.path.normpath(story_dir))
            object_name = f"videos/{task_id}/{video_name}.mp4"
            r2_url = await self.storage_service.upload_to_r2(video_path, object_name)
            logger.info(f"Final video uploaded to R2: {r2_url}")
            
            if not r2_url:
                raise ValueError("Failed to upload video to R2")
            
            # Use public R2 URL format
            public_url = f"https://pub-b9f9db5f1fcd4c7fa65abaa742ab9de0.r2.dev/{object_name}"
            
            # Calculate total cost from image generation and video clips
            total_cost = 0.0
            image_gen_cost = 0.0
            video_clip_cost = 0.0
            
            for image in images:
                if image.image_generation_cost is not None:
                    image_gen_cost += image.image_generation_cost
                    total_cost += image.image_generation_cost
                if image.video_clip_cost is not None:
                    video_clip_cost += image.video_clip_cost
                    total_cost += image.video_clip_cost
            
            logger.info(f"💰 Runware costs for task {task_id}:")
            logger.info(f"   📸 Image generation: ${image_gen_cost:.6f}")
            logger.info(f"   🎬 Video clips: ${video_clip_cost:.6f}")
            logger.info(f"   💵 Total: ${total_cost:.6f}")
            
            # Update task with final video URL and total cost
            update_data = {
                "url": public_url,
                "story_title": task.custom_title or task.story_title,
                "story_description": task.story_description or f"A {task.story_style_descriptor} video story",
                "status": "completed",
                "progress": 1.0,
                "status_message": "Video ready!",
                "total_cost": total_cost
            }
            await task.update(task_id=task_id, **update_data)
            
            logger.info(f"Video finalization completed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error finalizing video: {str(e)}")
            await task.update(task_id=task_id, status="failed", error_message=f"Finalization failed: {str(e)}")
