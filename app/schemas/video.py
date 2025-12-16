from pydantic import BaseModel, field_validator, Field
from typing import List, Optional, Literal
from datetime import datetime
from .image import ImageStatus
from app.constants.story_types import STORY_STYLE_DESCRIPTORS

# Expanded art styles
ArtStyle = Literal[
    'photorealistic', 
    'cinematic', 
    'anime', 
    'comic-book', 
    'pixar-art',
    'oil-painting',
    'watercolor',
    'sketch',
    'noir',
    'cyberpunk',
    'fantasy',
    'minimalist',
    'impressionist',
    'pop-art',
    'steampunk'
]

Duration = Literal['short', 'long']
Language = Literal['english', 'czech', 'danish', 'dutch', 'french', 'german', 'greek', 'hindi', 'indonesian', 'italian', 'chinese', 'japanese', 'norwegian', 'polish', 'portuguese', 'russian', 'spanish', 'swedish', 'turkish', 'ukrainian']
VoiceName = Literal['barbershop-man', 'calm-lady', 'female-conversational', 'female-narrator', 'male-conversational', 'male-narrator', 'friendly-sidekick']
Status = Literal['queued', 'processing', 'completed', 'failed']
StoryStyleDescriptor = Literal[tuple(STORY_STYLE_DESCRIPTORS)]  # Create Literal type from STORY_STYLE_DESCRIPTORS

class VideoRequest(BaseModel):
    custom_story: str = Field(..., min_length=100, description="The story script (required, minimum 100 characters)")
    custom_title: Optional[str] = Field(None, description="Optional custom title")
    story_style_descriptor: Optional[StoryStyleDescriptor] = Field(None, description="Optional visual tone modifier")
    art_style: ArtStyle
    duration: Duration
    language: Language
    voice_name: VoiceName

    @field_validator('story_style_descriptor', 'art_style', 'duration', 'language', 'voice_name', mode='before')
    def to_lowercase(cls, v):
        return v.lower() if isinstance(v, str) else v

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

