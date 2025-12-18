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
from pydantic import ValidationError

router = APIRouter()
video_task_processor = VideoTaskProcessor()

@router.get("/video/config")
async def get_video_config():
    """Get available configuration options for video generation"""
    return {
        "voices": settings.voices,
        "languages": settings.languages,
        "art_styles": settings.art_styles,
        "story_style_descriptors": settings.story_style_descriptors,
        "caption_fonts": settings.caption_fonts
    }

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
            urls=image.urls,
            subtitles=image.subtitles,
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
    """
    task = await VideoTask.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if task can be cancelled
    if task.status in ["completed"]:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed task")
    
    if task.status == "failed":
        raise HTTPException(status_code=400, detail="Task already failed")
    
    # Update task status to failed with cancellation message
    await task.update(
        task_id=task_id,
        status="failed",
        error_message="Task cancelled by user",
        status_message="Task cancelled"
    )
    
    return {
        "task_id": task_id,
        "status": "failed",
        "message": "Task cancelled successfully"
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
