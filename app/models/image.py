from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Float, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from app.db.base_class import Base
from app.db.session import async_session
from app.core.logging import logger

class Image(Base):
    __tablename__ = "images"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("video_tasks.id"), nullable=False, index=True)
    scene_number = Column(Integer, nullable=True, index=True)  # Scene order from storyboard
    audio_duration = Column(Float, nullable=True)  # Scene duration in seconds (from audio)
    urls = Column(JSONB, default=list)
    subtitles = Column(Text)
    enhanced_prompt = Column(Text)
    video_generation_request = Column(JSONB, nullable=True)  # Seadance 1.0 video generation request
    error_message = Column(Text)
    status = Column(Enum('queued', 'processing', 'completed', 'failed', name='image_status'), nullable=False, index=True)
    
    # Video clip fields (for animated clips from static images)
    video_clip_task_uuid = Column(String, nullable=True, index=True)  # Runware task UUID
    video_clip_url = Column(String, nullable=True)  # Generated video clip URL
    video_clip_status = Column(String, nullable=True)  # pending/processing/completed/failed
    video_clip_cost = Column(Float, nullable=True)  # API cost tracking
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    task = relationship("VideoTask", back_populates="images")

    @classmethod
    async def create(cls, **kwargs) -> Optional['Image']:
        try:
            async with async_session() as session:
                image = cls(**kwargs)
                session.add(image)
                await session.commit()
                await session.refresh(image)
            return image
        except SQLAlchemyError as e:
            logger.error(f"Error creating image in database: {e}")
            return None

    @classmethod
    async def get(cls, image_id: str) -> Optional['Image']:
        async with async_session() as session:
            return await session.get(cls, image_id)

    @classmethod
    async def update(cls, image_id: str, **kwargs) -> Optional['Image']:
        async with async_session() as session:
            image = await session.get(cls, image_id)
            if image:
                for key, value in kwargs.items():
                    setattr(image, key, value)
                await session.commit()
                await session.refresh(image)
            return image

    @classmethod
    async def delete(cls, image_id: str) -> bool:
        async with async_session() as session:
            image = await session.get(cls, image_id)
            if image:
                await session.delete(image)
                await session.commit()
                return True
            return False

    @classmethod
    async def list_by_task(cls, task_id: str, limit: int = 100, offset: int = 0) -> List['Image']:
        async with async_session() as session:
            query = select(cls).filter(cls.task_id == task_id).limit(limit).offset(offset)
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def get_by_task_and_status(cls, task_id: str, status: str) -> List['Image']:
        async with async_session() as session:
            query = select(cls).filter(cls.task_id == task_id, cls.status == status)
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def update_by_task_and_scene(cls, task_id: str, scene_number: int, **kwargs) -> Optional['Image']:
        """Update an image by task_id and scene_number"""
        try:
            async with async_session() as session:
                query = select(cls).filter(cls.task_id == task_id, cls.scene_number == scene_number)
                result = await session.execute(query)
                image = result.scalar_one_or_none()
                if image:
                    for key, value in kwargs.items():
                        setattr(image, key, value)
                    await session.commit()
                    await session.refresh(image)
                    logger.info(f"Updated image for task {task_id} scene {scene_number}: {kwargs}")
                    return image
                else:
                    logger.warning(f"No image found for task {task_id} scene {scene_number}")
                    return None
        except SQLAlchemyError as e:
            logger.error(f"Error updating image by task and scene: {e}")
            return None