"""
Video clip generation endpoint - generates animated clips from static images
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from pydantic import BaseModel
from app.core.logging import logger
from app.db.session import async_session
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models.image import Image
from app.services.runware_video_sdk import generate_video_from_image
import asyncio
import uuid as uuid_lib

router = APIRouter()


class VideoClipGenerationRequest(BaseModel):
    duration: Optional[int] = 2
    fps: Optional[int] = 24


class VideoClipResponse(BaseModel):
    task_id: str
    scenes_submitted: int
    message: str


async def process_video_clips_background(task_id: str, duration: int = 2, fps: int = 24):
    """Background task to generate video clips for KEY scenes only (first, two middle, last)"""
    
    try:
        async with async_session() as session:
            # Get ALL scenes for this task to determine total count
            all_scenes_result = await session.execute(
                select(Image).where(Image.task_id == task_id).order_by(Image.created_at)
            )
            all_scenes = all_scenes_result.scalars().all()
            total_scenes = len(all_scenes)
            
            logger.info(f"Task has {total_scenes} total scenes")
            
            # Determine which scene POSITIONS are key scenes (based on total scenes)
            key_scene_indices = set()
            if total_scenes > 0:
                key_scene_indices.add(0)  # First scene
            if total_scenes > 3:
                mid_point = total_scenes // 2
                key_scene_indices.add(mid_point - 1)
                key_scene_indices.add(mid_point)
            if total_scenes > 1:
                key_scene_indices.add(total_scenes - 1)  # Last scene
            
            logger.info(f"Key scene positions (0-indexed): {sorted(key_scene_indices)}")
            
            # Collect scenes to process - ANY scene with video_generation_request
            # (not just calculated key scenes, to handle legacy data)
            scenes_to_process = []
            for idx, scene in enumerate(all_scenes):
                # Process any scene that has a video generation request
                if scene.video_generation_request:
                    scenes_to_process.append((idx, scene))
                    logger.info(f"Found scene at position {idx} with video_generation_request")
            
            if not scenes_to_process:
                logger.info("No key scenes to process for video clip generation")
                return
            
            logger.info(f"Processing {len(scenes_to_process)} key scenes in parallel")
            
            # Generate all video clips in parallel
            async def generate_clip_for_scene(idx, scene):
                try:
                    # Get image URL
                    urls = scene.urls
                    if not urls or len(urls) == 0:
                        logger.warning(f"Scene {scene.id} has no image URLs")
                        return
                    
                    image_url = urls[0]
                    
                    # Get video generation request
                    video_req = scene.video_generation_request
                    if not video_req or 'prompt' not in video_req:
                        logger.warning(f"Scene {scene.id} has invalid video_generation_request")
                        return
                    
                    prompt = video_req['prompt']
                    
                    # Generate unique task UUID for this clip
                    clip_task_uuid = str(uuid_lib.uuid4())
                    
                    # Update scene status to processing
                    async with async_session() as update_session:
                        scene_to_update = await update_session.get(Image, scene.id)
                        scene_to_update.video_clip_task_uuid = clip_task_uuid
                        scene_to_update.video_clip_status = 'processing'
                        await update_session.commit()
                    
                    logger.info(f"Generating video clip for scene {scene.id} (position {idx})")
                    logger.debug(f"Image: {image_url}")
                    logger.debug(f"Prompt: {prompt[:100]}...")
                    
                    # Generate video clip with cancellation support
                    async with async_session() as check_session:
                        video_url = await generate_video_from_image(
                            image_url=image_url,
                            prompt=prompt,
                            duration=duration,
                            fps=fps,
                            db_session=check_session,
                            image_id=scene.id
                        )
                    
                    # Check for cancellation one more time after generation
                    async with async_session() as final_check_session:
                        final_scene = await final_check_session.get(Image, scene.id)
                        if final_scene and final_scene.video_clip_status in ['failed', 'cancelled']:
                            logger.info(f"Video clip generation for scene {scene.id} was cancelled")
                            return
                    
                    # Update scene with result
                    async with async_session() as update_session:
                        scene_to_update = await update_session.get(Image, scene.id)
                        if video_url:
                            scene_to_update.video_clip_url = video_url
                            scene_to_update.video_clip_status = 'completed'
                            logger.info(f"✅ Video clip generated for scene {scene.id}: {video_url}")
                        else:
                            scene_to_update.video_clip_status = 'failed'
                            logger.error(f"❌ Failed to generate video clip for scene {scene.id}")
                        await update_session.commit()
                    
                except Exception as e:
                    logger.error(f"Error generating video clip for scene {scene.id}: {e}")
                    async with async_session() as update_session:
                        scene_to_update = await update_session.get(Image, scene.id)
                        scene_to_update.video_clip_status = 'failed'
                        await update_session.commit()
            
            # Process all scenes in parallel
            await asyncio.gather(*[
                generate_clip_for_scene(idx, scene)
                for idx, scene in scenes_to_process
            ])
            
            logger.info(f"Completed video clip generation for task {task_id}")
            
    except Exception as e:
        logger.error(f"Error in background video clip processing: {e}")


async def process_video_clips_background_with_durations(task_id: str, fps: int = 24):
    """
    Background task to generate video clips for SELECTED scenes only:
    - First scene
    - Last scene  
    - One interesting middle scene (longest duration or most complex description)
    
    Uses actual audio_duration for each scene instead of fixed 2 seconds.
    """
    
    try:
        async with async_session() as session:
            # Get ALL scenes ordered by scene_number
            all_scenes_result = await session.execute(
                select(Image)
                .where(Image.task_id == task_id)
                .order_by(Image.scene_number)
            )
            all_scenes = all_scenes_result.scalars().all()
            total_scenes = len(all_scenes)
            
            if total_scenes == 0:
                logger.warning(f"No scenes found for task {task_id}")
                return
            
            logger.info(f"Task {task_id} has {total_scenes} scenes - selecting first, last, and interesting middle")
            
            # Select scenes to animate
            scenes_to_animate = []
            
            # Always include first scene
            scenes_to_animate.append(all_scenes[0])
            logger.info(f"Selected first scene: {all_scenes[0].scene_number}")
            
            # Always include last scene (if more than 1 scene)
            if total_scenes > 1:
                scenes_to_animate.append(all_scenes[-1])
                logger.info(f"Selected last scene: {all_scenes[-1].scene_number}")
            
            # Select one interesting middle scene (if more than 2 scenes)
            if total_scenes > 2:
                # Get middle third of scenes
                middle_start = total_scenes // 3
                middle_end = (2 * total_scenes) // 3
                middle_candidates = all_scenes[middle_start:middle_end]
                
                if middle_candidates:
                    # Pick scene with longest audio duration
                    # (more narration = more important scene)
                    interesting_scene = max(
                        middle_candidates, 
                        key=lambda s: s.audio_duration if s.audio_duration else 0
                    )
                    scenes_to_animate.append(interesting_scene)
                    logger.info(f"Selected interesting middle scene: {interesting_scene.scene_number} "
                              f"(duration: {interesting_scene.audio_duration:.2f}s)")
            
            logger.info(f"Generating video clips for {len(scenes_to_animate)} scenes")
            
            # Generate video clips in parallel
            async def generate_clip_for_scene(scene):
                try:
                    # Get image URL
                    urls = scene.urls
                    if not urls or len(urls) == 0:
                        logger.warning(f"Scene {scene.scene_number} has no image URLs")
                        return
                    
                    image_url = urls[0]
                    
                    # Get duration from audio (fallback to 2 seconds if not available)
                    scene_duration = int(scene.audio_duration) if scene.audio_duration else 2
                    logger.info(f"Scene {scene.scene_number}: Using duration {scene_duration}s "
                              f"(audio_duration: {scene.audio_duration})")
                    
                    # For animated scenes, create a video generation prompt
                    # Use existing video_generation_request if available, otherwise create basic one
                    if scene.video_generation_request and 'prompt' in scene.video_generation_request:
                        prompt = scene.video_generation_request['prompt']
                    else:
                        # Create basic animation prompt from subtitles
                        prompt = f"Gentle camera movement, subtle zoom, {scene.subtitles[:100]}"
                    
                    # Generate unique task UUID for this clip
                    clip_task_uuid = str(uuid_lib.uuid4())
                    
                    # Update scene status to processing
                    async with async_session() as update_session:
                        scene_to_update = await update_session.get(Image, scene.id)
                        scene_to_update.video_clip_task_uuid = clip_task_uuid
                        scene_to_update.video_clip_status = 'processing'
                        await update_session.commit()
                    
                    logger.info(f"Generating {scene_duration}s video clip for scene {scene.scene_number}")
                    logger.debug(f"Image: {image_url}")
                    logger.debug(f"Prompt: {prompt[:100]}...")
                    
                    # Generate video clip with actual scene duration
                    async with async_session() as check_session:
                        video_url = await generate_video_from_image(
                            image_url=image_url,
                            prompt=prompt,
                            duration=scene_duration,  # Use actual duration!
                            fps=fps,
                            db_session=check_session,
                            image_id=scene.id
                        )
                    
                    # Check for cancellation
                    async with async_session() as final_check_session:
                        final_scene = await final_check_session.get(Image, scene.id)
                        if final_scene and final_scene.video_clip_status in ['failed', 'cancelled']:
                            logger.info(f"Video clip generation for scene {scene.scene_number} was cancelled")
                            return
                    
                    # Update scene with result
                    async with async_session() as update_session:
                        scene_to_update = await update_session.get(Image, scene.id)
                        if video_url:
                            scene_to_update.video_clip_url = video_url
                            scene_to_update.video_clip_status = 'completed'
                            logger.info(f"✅ Video clip generated for scene {scene.scene_number}: {video_url}")
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
            await asyncio.gather(*[
                generate_clip_for_scene(scene)
                for scene in scenes_to_animate
            ])
            
            logger.info(f"Completed video clip generation for task {task_id}")
            
    except Exception as e:
        logger.error(f"Error in background video clip processing with durations: {e}")


@router.post("/tasks/{task_id}/generate-video-clips", response_model=VideoClipResponse)
async def generate_video_clips(
    task_id: str,
    request: VideoClipGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate animated video clips from static images for KEY scenes only.
    Generates clips for 4 key scenes: first, two middle scenes, and last.
    This runs asynchronously in the background.
    """
    
    try:
        async with async_session() as session:
            # Get TOTAL number of scenes to determine key positions
            all_scenes_result = await session.execute(
                select(Image).where(Image.task_id == task_id).order_by(Image.created_at)
            )
            all_scenes = all_scenes_result.scalars().all()
            total_scenes = len(all_scenes)
            
            if total_scenes == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No scenes found for this task"
                )
            
            # Calculate key scene positions
            key_scene_indices = set()
            if total_scenes > 0:
                key_scene_indices.add(0)  # First
            if total_scenes > 3:
                mid_point = total_scenes // 2
                key_scene_indices.add(mid_point - 1)
                key_scene_indices.add(mid_point)
            if total_scenes > 1:
                key_scene_indices.add(total_scenes - 1)  # Last
            
            # Check how many scenes have video_generation_request (not just key scenes)
            scenes_with_video_request = 0
            actual_scene_indices = []
            for idx, scene in enumerate(all_scenes):
                if scene.video_generation_request:
                    scenes_with_video_request += 1
                    actual_scene_indices.append(idx)
            
            if scenes_with_video_request == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No scenes with video generation prompts found for this task"
                )
            
            # Add background task
            background_tasks.add_task(
                process_video_clips_background,
                task_id,
                request.duration,
                request.fps
            )
            
            return VideoClipResponse(
                task_id=task_id,
                scenes_submitted=scenes_with_video_request,
                message=f"Video clip generation started for {scenes_with_video_request} scenes (out of {total_scenes} total). Scene positions: {sorted(actual_scene_indices)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting video clip generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/video-clips-status")
async def get_video_clips_status(task_id: str):
    """Get the status of video clip generation for a task"""
    
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Image).where(
                    and_(
                        Image.task_id == task_id,
                        Image.video_generation_request.isnot(None)
                    )
                ).order_by(Image.created_at)
            )
            scenes = result.scalars().all()
            
            if not scenes:
                raise HTTPException(
                    status_code=404,
                    detail="No scenes with video prompts found for this task"
                )
            
            clips_status = []
            for scene in scenes:
                clips_status.append({
                    "scene_id": scene.id,
                    "enhanced_prompt": scene.enhanced_prompt[:100] + "..." if scene.enhanced_prompt else None,
                    "video_clip_status": scene.video_clip_status,
                    "video_clip_url": scene.video_clip_url,
                    "video_clip_cost": scene.video_clip_cost,
                    "video_clip_task_uuid": scene.video_clip_task_uuid
                })
            
            total = len(clips_status)
            completed = sum(1 for c in clips_status if c['video_clip_status'] == 'completed')
            processing = sum(1 for c in clips_status if c['video_clip_status'] == 'processing')
            failed = sum(1 for c in clips_status if c['video_clip_status'] == 'failed')
            pending = sum(1 for c in clips_status if not c['video_clip_status'])
            
            return {
                "task_id": task_id,
                "summary": {
                    "total": total,
                    "completed": completed,
                    "processing": processing,
                    "failed": failed,
                    "pending": pending
                },
                "clips": clips_status
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video clips status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/finalize-video")
async def finalize_video(task_id: str, background_tasks: BackgroundTasks):
    """
    Finalize the video by stitching together video clips (or static images for scenes without clips).
    Should be called AFTER video clips have been generated.
    """
    
    try:
        async with async_session() as session:
            # Check if all key scenes have completed video clips
            result = await session.execute(
                select(Image).where(Image.task_id == task_id).order_by(Image.created_at)
            )
            scenes = result.scalars().all()
            
            if not scenes:
                raise HTTPException(status_code=404, detail="No scenes found for this task")
            
            # Count video clip statuses for ALL scenes with video_generation_request
            # (not just calculated key scenes, to handle legacy data)
            scenes_with_clips = []
            for idx, scene in enumerate(scenes):
                if scene.video_generation_request:
                    scenes_with_clips.append(scene)
            
            if not scenes_with_clips:
                raise HTTPException(
                    status_code=400,
                    detail="No scenes with video generation requests found"
                )
            
            completed = sum(1 for s in scenes_with_clips if s.video_clip_status == 'completed')
            processing = sum(1 for s in scenes_with_clips if s.video_clip_status == 'processing')
            failed = sum(1 for s in scenes_with_clips if s.video_clip_status == 'failed')
            
            if processing > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"{processing} video clips are still processing. Wait for them to complete before finalizing."
                )
            
            if completed == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No video clips have been generated yet. Generate clips first using /generate-video-clips"
                )
            
            # Trigger background task to finalize the video
            from app.services.video_task_processor import VideoTaskProcessor
            processor = VideoTaskProcessor()
            background_tasks.add_task(processor.finalize_video_with_clips, task_id)
            
            return {
                "task_id": task_id,
                "message": f"Video finalization started. {completed}/{len(scenes_with_clips)} scenes have video clips. {failed} failed.",
                "scenes_with_video_requests": len(scenes_with_clips),
                "clips_completed": completed,
                "clips_failed": failed
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finalizing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))
