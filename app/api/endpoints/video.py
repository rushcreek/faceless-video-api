from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, HTTPException
from app.schemas.video import VideoRequest, VideoResponse, VideoTaskStatus
from app.core.security import get_current_user
from app.core.config import settings
from app.models.video_task import VideoTask
from app.services.video_task_processor import VideoTaskProcessor
from uuid import uuid4
from app.models.image import Image
from app.schemas.image import ImageStatus
import logging
import json
import os
from pydantic import ValidationError
from typing import Dict, Any

router = APIRouter()
video_task_processor = VideoTaskProcessor()
logger = logging.getLogger(__name__)

@router.get("/video/config")
async def get_video_config():
    """Get available configuration options for video generation"""
    return {
        "voices": settings.voices,
        "languages": settings.languages,
        "art_styles": settings.art_styles,
        "story_style_descriptors": settings.story_style_descriptors,
        "caption_fonts": settings.caption_fonts,
        "video_settings": settings.video_settings,
        "product_mention": settings.product_mention,
        "ai_prompts": settings.ai_prompts if hasattr(settings, 'ai_prompts') else None,
        "ai_system_prompts": settings.ai_system_prompts if hasattr(settings, 'ai_system_prompts') else None
    }

@router.put("/video/config")
async def update_video_config(
    config_update: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update video generation settings (video_settings, product_mention, ai_prompts, ai_system_prompts)"""
    try:
        config_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'config.json')
        
        # Read existing config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update only allowed settings
        if 'video_settings' in config_update:
            config['video_settings'] = config_update['video_settings']
            settings.video_settings = config_update['video_settings']
        
        if 'product_mention' in config_update:
            config['product_mention'] = config_update['product_mention']
            settings.product_mention = config_update['product_mention']
        
        if 'ai_prompts' in config_update:
            config['ai_prompts'] = config_update['ai_prompts']
            settings.ai_prompts = config_update['ai_prompts']
        
        if 'ai_system_prompts' in config_update:
            config['ai_system_prompts'] = config_update['ai_system_prompts']
            settings.ai_system_prompts = config_update['ai_system_prompts']
        
        # Write back to config file
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Video config updated successfully")
        return {"status": "success", "message": "Configuration updated"}
        
    except Exception as e:
        logger.error(f"Error updating video config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video", response_model=VideoResponse)
async def generate_video(
    request: VideoRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    try:
        task_id = str(uuid4())
        
        await VideoTask.create(
            id=task_id, 
            status="queued", 
            progress=0.0, 
            story_style_descriptor=request.story_style_descriptor,
            tweak_prompt=request.tweak_prompt,
            art_style=request.art_style,
            duration=request.duration,
            language=request.language,
            voice_name=request.voice_name,
            caption_font=request.caption_font,
            custom_story=request.custom_story,
            custom_title=request.custom_title
        )
        
        background_tasks.add_task(
            video_task_processor.process_video_generation_task,
            task_id,
            request.art_style,
            request.duration,
            request.language,
            request.voice_name,
            request.custom_story,
            request.custom_title,
            request.story_style_descriptor,
            request.caption_font,
            request.tweak_prompt
        )
        
        return VideoResponse(task_id=task_id, status="queued")
    except ValidationError as e:
        logging.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in generate_video: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/video/tasks/{task_id}", response_model=VideoTaskStatus)
async def get_task_status(task_id: str, current_user: dict = Depends(get_current_user)):
    task = await VideoTask.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    images = await Image.list_by_task(task_id)
    return VideoTaskStatus(
        task_id=task.id,
        status=task.status,
        progress=task.progress,
        url=task.url,
        story_title=task.story_title,
        story_description=task.story_description,
        story_text=task.story_text,
        error_message=task.error_message,
        images=[ImageStatus(
            id=image.id,
            status=image.status,
            scene_number=image.scene_number,
            urls=image.urls,
            subtitles=image.subtitles,
            enhanced_prompt=image.enhanced_prompt,
            video_generation_request=image.video_generation_request,
            video_clip_url=image.video_clip_url,
            created_at=image.created_at,
            updated_at=image.updated_at
        ) for image in images],
        created_at=task.created_at,
        updated_at=task.updated_at
    )

@router.post("/video/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """
    Cancel a running or queued video generation task.
    This will mark the task as failed and stop further processing.
    
    Note: For video clips being generated via Runware, this stops polling
    but the videos may still complete on Runware's servers.
    """
    task = await VideoTask.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if task can be cancelled
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed task")
    
    # If already failed/cancelled, return success (idempotent)
    if task.status == "failed":
        logger.info(f"Task {task_id} already cancelled/failed")
        return {
            "task_id": task_id,
            "status": "failed",
            "message": "Task already cancelled",
            "clips_cancelled": 0
        }
    
    # Update task status to failed with cancellation message
    await task.update(
        task_id=task_id,
        status="failed",
        error_message="Task cancelled by user",
        status_message="Task cancelled"
    )
    
    # Also cancel any video clips being generated
    from app.models.image import Image
    images = await Image.list_by_task(task_id)
    cancelled_clips = 0
    for image in images:
        if image.video_clip_status == 'processing':
            await image.update(
                image_id=image.id,
                video_clip_status='failed',
                error_message='Cancelled by user'
            )
            cancelled_clips += 1
    
    logger.info(f"Task {task_id} cancelled by user. {cancelled_clips} video clips cancelled.")
    
    return {
        "task_id": task_id,
        "status": "failed",
        "message": f"Task cancelled successfully. {cancelled_clips} video clips stopped.",
        "clips_cancelled": cancelled_clips
    }

@router.delete("/video/tasks/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """
    Delete a completed or failed video generation task from the database.
    This will permanently remove the task and all associated images.
    
    Note: Only completed or failed tasks can be deleted.
    """
    task = await VideoTask.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Only allow deletion of completed or failed tasks
    if task.status not in ["completed", "failed"]:
        raise HTTPException(
            status_code=400, 
            detail="Only completed or failed tasks can be deleted. Cancel active tasks first."
        )
    
    # Delete associated images first
    from app.models.image import Image
    images = await Image.list_by_task(task_id)
    for image in images:
        await Image.delete(image.id)
    
    # Delete the task
    success = await VideoTask.delete(task_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete task")
    
    logger.info(f"Task {task_id} and {len(images)} associated images deleted by user")
    
    return {
        "task_id": task_id,
        "message": f"Task and {len(images)} associated images deleted successfully"
    }

@router.get("/video/tasks")
async def list_tasks(
    limit: int = 20,
    status: str = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List all video generation tasks with optional status filter.
    Returns tasks ordered by creation date (newest first).
    """
    tasks = await VideoTask.list_all(limit=limit, status_filter=status)
    
    return {
        "tasks": [{
            "task_id": task.id,
            "status": task.status,
            "progress": task.progress,
            "status_message": task.status_message,
            "custom_title": task.custom_title,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        } for task in tasks],
        "total": len(tasks)
    }

@router.post("/video/tasks/{task_id}/images/{image_id}/regenerate")
async def regenerate_scene(
    task_id: str,
    image_id: str,
    updates: dict,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Regenerate a specific scene's image and/or video with updated prompts.
    
    Request body can contain:
    - image_prompt: New prompt for image regeneration
    - video_generation_request: Updated video generation parameters
        - prompt: New motion prompt
        - negative_prompt: New negative prompt
    """
    from app.db.session import async_session
    from sqlalchemy.future import select
    
    # Verify task exists
    task = await VideoTask.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get the image
    async with async_session() as session:
        result = await session.execute(
            select(Image).where(Image.id == image_id, Image.task_id == task_id)
        )
        image = result.scalar_one_or_none()
        
        if not image:
            raise HTTPException(status_code=404, detail="Image not found in this task")
        
        # Update image prompt if provided
        if "image_prompt" in updates:
            image.enhanced_prompt = updates["image_prompt"]
            # TODO: Trigger image regeneration in background
            logger.info(f"Updated image prompt for image {image_id}")
        
        # Update video generation request if provided
        if "video_generation_request" in updates:
            current_req = image.video_generation_request or {}
            video_updates = updates["video_generation_request"]
            
            if "prompt" in video_updates:
                current_req["prompt"] = video_updates["prompt"]
            if "negative_prompt" in video_updates:
                current_req["negative_prompt"] = video_updates["negative_prompt"]
            
            image.video_generation_request = current_req
            # TODO: Trigger video clip regeneration in background
            logger.info(f"Updated video prompts for image {image_id}")
        
        await session.commit()
    
    return {
        "task_id": task_id,
        "image_id": image_id,
        "message": "Prompts updated successfully. Regeneration functionality coming soon.",
        "updates": updates
    }
