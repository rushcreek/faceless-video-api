from pydantic import BaseModel, field_validator, Field
from typing import List, Optional, Literal
from datetime import datetime
from .image import ImageStatus
from app.core.config import settings

# Type aliases using str instead of Literal for dynamic config
Status = Literal['queued', 'processing', 'completed', 'failed']
Duration = Literal['short', 'long']

class VideoRequest(BaseModel):
    custom_story: str = Field(..., min_length=100, description="The story script (required, minimum 100 characters)")
    custom_title: Optional[str] = Field(None, description="Optional custom title")
    story_style_descriptor: Optional[str] = Field(None, description="Optional visual tone modifier")
    tweak_prompt: Optional[str] = Field(None, description="Optional prompt to refine image generation")
    art_style: str
    duration: Duration = Field(default='long', description="Duration setting (auto-determined from story length)")
    language: str
    voice_name: str
    caption_font: str = Field(default='BebasNeue', description="Font for video captions")

    @field_validator('story_style_descriptor', 'art_style', 'duration', 'language', 'voice_name', 'caption_font', mode='before')
    def to_lowercase(cls, v):
        return v if isinstance(v, str) else v
    
    @field_validator('art_style')
    def validate_art_style(cls, v):
        if v not in settings.art_styles:
            raise ValueError(f"Invalid art_style. Must be one of: {', '.join(settings.art_styles)}")
        return v
    
    @field_validator('language')
    def validate_language(cls, v):
        if v not in settings.languages:
            raise ValueError(f"Invalid language. Must be one of: {', '.join(settings.languages)}")
        return v
    
    @field_validator('voice_name')
    def validate_voice_name(cls, v):
        voice_ids = [voice['id'] for voice in settings.voices]
        if v not in voice_ids:
            raise ValueError(f"Invalid voice_name. Must be one of: {', '.join(voice_ids)}")
        return v
    
    @field_validator('story_style_descriptor')
    def validate_story_style_descriptor(cls, v):
        if v and v not in settings.story_style_descriptors:
            raise ValueError(f"Invalid story_style_descriptor. Must be one of: {', '.join(settings.story_style_descriptors)}")
        return v
    
    @field_validator('caption_font')
    def validate_caption_font(cls, v):
        if v not in settings.caption_fonts:
            raise ValueError(f"Invalid caption_font. Must be one of: {', '.join(settings.caption_fonts)}")
        return v

class VideoResponse(BaseModel):
    task_id: str
    status: Status

class VideoTaskStatus(BaseModel):
    task_id: str
    status: Status
    progress: float
    url: Optional[str] = None
    story_title: Optional[str] = None
    story_description: Optional[str] = None
    story_text: Optional[str] = None
    images: List[ImageStatus]
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

