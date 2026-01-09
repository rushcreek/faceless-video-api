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

            # NOTE: Image saving to database is now handled AFTER generate_video completes,
            # since images are generated inside generate_video after caption timing is determined.
            # Audio generation is also handled inside generate_video now.

            await task.update(task_id=task_id, progress=0.50, status_message="Ready for video generation")

            # Check if task was cancelled
            task = await VideoTask.get(task_id)
            if task.status == "failed":
                logger.info(f"Task {task_id} was cancelled, stopping before video generation")
                return

            # Skip audio generation here - it's now handled inside generate_video

            # Step 5: Generate video directly with the storyboard_project we have
            # This will: generate audio, transcribe, generate image prompts, generate images, save to DB, and create video
            await task.update(
                task_id=task_id,
                progress=0.55,
                status_message="Generating video with images and captions..."
            )
            
            try:
                # Progress callback
                async def video_progress_callback(progress_value, message):
                    await task.update(task_id=task_id, progress=round(progress_value, 2), status_message=message)
                
                # Generate final video directly with storyboard_project
                video_path = await self.video_generator.generate_video(
                    storyboard_project,
                    story_dir,
                    voice_name,
                    task.caption_font or 'BebasNeue',
                    progress_callback=video_progress_callback,
                    task_id=task_id
                )
                
                if not video_path:
                    raise ValueError("Failed to create final video")
                
                # Step 6: Generate video clips for key scenes (images are now in DB)
                logger.info(f"🎬 Starting video clip generation for key scenes...")
                await task.update(task_id=task_id, progress=0.65, status_message="Generating animated video clips...")
                
                # Get images that need video clips (those with video_generation_request)
                images = await Image.list_by_task(task_id)
                scenes_with_video_requests = [img for img in images if img.video_generation_request]
                
                if scenes_with_video_requests:
                    logger.info(f"Found {len(scenes_with_video_requests)} scenes with video generation requests")
                    await self._generate_video_clips_for_scenes(task_id, scenes_with_video_requests, task)
                else:
                    logger.info("No scenes require video clip generation")
                
                # Step 7: Regenerate final video WITH video clips
                logger.info(f"🎥 Regenerating final video with animated clips...")
                await task.update(task_id=task_id, progress=0.80, status_message="Creating final video with animations...")
                
                # Get updated images (now with video_clip_url populated)
                images = await Image.list_by_task(task_id)
                
                # Recreate storyboard with video clips
                for idx, scene in enumerate(storyboard_project["storyboards"]):
                    if idx < len(images):
                        scene["video_clip_url"] = images[idx].video_clip_url
                
                # Regenerate video with clips
                video_path_with_clips = await self.video_generator.generate_video(
                    storyboard_project,
                    story_dir,
                    voice_name,
                    task.caption_font or 'BebasNeue',
                    progress_callback=video_progress_callback,
                    task_id=task_id
                )
                
                if video_path_with_clips:
                    # Upload the new video with clips
                    logger.info("Uploading final video with clips to R2...")
                    await task.update(task_id=task_id, progress=0.98, status_message="Uploading final video...")
                    video_name = os.path.basename(os.path.normpath(story_dir))
                    object_name = f"videos/{task_id}/{video_name}.mp4"
                    r2_url = await self.storage_service.upload_to_r2(video_path_with_clips, object_name)
                    
                    if r2_url:
                        public_url = f"https://pub-b9f9db5f1fcd4c7fa65abaa742ab9de0.r2.dev/{object_name}"
                        logger.info(f"Final video with clips uploaded: {public_url}")
                
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
                
                logger.info(f"💰 Total cost for task {task_id}:")
                logger.info(f"   📸 Image generation: ${image_gen_cost:.6f}")
                logger.info(f"   🎬 Video clips: ${video_clip_cost:.6f}")
                logger.info(f"   💵 Total: ${total_cost:.6f}")
                
                # Update task with final video URL and total cost
                await task.update(
                    task_id=task_id,
                    url=public_url,
                    story_title=task.custom_title or task.story_title,
                    story_description=task.story_description or f"A {task.story_style_descriptor} video story",
                    status="completed",
                    progress=1.0,
                    status_message="Video ready!",
                    total_cost=total_cost
                )
                
                logger.info(f"Video generation completed successfully for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to generate video: {str(e)}")
                await task.update(
                    task_id=task_id,
                    status="failed",
                    error_message=f"Video generation failed: {str(e)}"
                )
                return
            
            # Video complete
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

    async def _generate_video_clips_for_scenes(self, task_id: str, scenes: list, task):
        """
        Generate video clips for scenes that have video_generation_request.
        This is called automatically during the main video generation flow.
        """
        from app.services.runware_video_sdk import generate_video_from_image
        from app.db.session import async_session
        import math
        
        logger.info(f"🎬 Generating video clips for {len(scenes)} scenes")
        
        async def generate_clip_for_scene(scene):
            try:
                logger.info(f"🎥 Processing scene {scene.scene_number}")
                
                # Get image URL
                urls = scene.urls
                if not urls or len(urls) == 0:
                    logger.warning(f"Scene {scene.scene_number} has no image URLs")
                    return
                
                image_url = urls[0]
                
                # Get duration from audio (fallback to 2 seconds if not available)
                duration = scene.audio_duration or 2
                logger.info(f"  📏 Scene duration: {duration}s")
                
                # Validate and round duration
                if duration < 1:
                    logger.warning(f"  ⚠️ Duration {duration}s too short, using minimum 2s")
                    duration = 2
                elif duration > 10:
                    logger.warning(f"  ⚠️ Duration {duration}s too long, capping at 10s")
                    duration = 10
                
                scene_duration = math.ceil(duration)
                logger.info(f"  ✅ Using duration: {scene_duration}s for Runware API")
                
                # Get video generation prompt
                if scene.video_generation_request and 'prompt' in scene.video_generation_request:
                    prompt = scene.video_generation_request['prompt']
                else:
                    # Create basic animation prompt from subtitles
                    prompt = f"Gentle camera movement, subtle zoom, {scene.subtitles[:100]}"
                
                # Generate unique task UUID for this clip
                import uuid as uuid_lib
                clip_task_uuid = str(uuid_lib.uuid4())
                
                # Update scene status to processing
                async with async_session() as update_session:
                    scene_to_update = await update_session.get(Image, scene.id)
                    scene_to_update.video_clip_task_uuid = clip_task_uuid
                    scene_to_update.video_clip_status = 'processing'
                    await update_session.commit()
                
                logger.info(f"  🎬 Generating {scene_duration}s video clip for scene {scene.scene_number}")
                logger.debug(f"  Image: {image_url}")
                logger.debug(f"  Prompt: {prompt[:100]}...")
                
                # Generate video clip with actual scene duration
                async with async_session() as check_session:
                    result = await generate_video_from_image(
                        image_url=image_url,
                        prompt=prompt,
                        duration=scene_duration,
                        fps=24,
                        db_session=check_session,
                        image_id=scene.id
                    )
                
                # Extract URL and cost from result
                video_url = None
                video_cost = None
                if isinstance(result, dict):
                    video_url = result.get('url')
                    video_cost = result.get('cost')
                elif isinstance(result, str):
                    video_url = result  # Legacy string return
                
                # Check for cancellation
                async with async_session() as final_check_session:
                    final_scene = await final_check_session.get(Image, scene.id)
                    if final_scene and final_scene.video_clip_status in ['failed', 'cancelled']:
                        logger.info(f"  ℹ️ Video clip generation for scene {scene.scene_number} was cancelled")
                        return
                
                # Update scene with result
                async with async_session() as update_session:
                    scene_to_update = await update_session.get(Image, scene.id)
                    if video_url:
                        scene_to_update.video_clip_url = video_url
                        scene_to_update.video_clip_cost = video_cost
                        scene_to_update.video_clip_status = 'completed'
                        cost_str = f" (cost: ${video_cost})" if video_cost is not None else ""
                        logger.info(f"✅ Video clip generated for scene {scene.scene_number}: {video_url}{cost_str}")
                    else:
                        scene_to_update.video_clip_status = 'failed'
                        logger.error(f"❌ Failed to generate video clip for scene {scene.scene_number}")
                    await update_session.commit()
                
            except Exception as e:
                logger.error(f"Error generating video clip for scene {scene.scene_number}: {e}")
                async with async_session() as update_session:
                    scene_to_update = await update_session.get(Image, scene.id)
                    scene_to_update.video_clip_status = 'failed'
                    await update_session.commit()
        
        # Process all selected scenes in parallel
        logger.info(f"🎥 Starting parallel video generation for {len(scenes)} scenes")
        results = await asyncio.gather(*[
            generate_clip_for_scene(scene)
            for scene in scenes
        ], return_exceptions=True)
        
        # Log any exceptions that occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Exception in scene {scenes[i].scene_number}: {result}", exc_info=result)
        
        logger.info(f"✅ Completed video clip generation for task {task_id}")

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
