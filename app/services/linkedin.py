"""
LinkedIn API Service for posting videos to LinkedIn.

Supports posting text, images, videos, and documents to LinkedIn.
Requires LINKEDIN_ACCESS_TOKEN and LINKEDIN_MEMBER_URN environment variables.
"""

import os
import mimetypes
import time
import tempfile
import logging
import aiohttp
import asyncio
from typing import Optional
from app.core.config import settings
from openai import AsyncAzureOpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def _get_openai_client():
    """Get the appropriate OpenAI client based on configuration."""
    if settings.use_azure_openai:
        return AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.azure_api_version,
            timeout=60.0,
            max_retries=2
        )
    else:
        return AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=60.0,
            max_retries=2
        )


async def generate_linkedin_caption(story_title: str, story_description: str = None, story_text: str = None) -> str:
    """
    Generate a short, curiosity-inducing caption for a LinkedIn video post.
    
    Args:
        story_title: Title of the video/story
        story_description: Optional description of the story
        story_text: Optional full story text (will be truncated for context)
        
    Returns:
        A short, engaging caption for LinkedIn
    """
    try:
        client = _get_openai_client()
        
        # Build context from available info
        context_parts = [f"Video Title: {story_title}"]
        if story_description:
            context_parts.append(f"Description: {story_description}")
        if story_text:
            # Truncate story to first 500 chars for context
            truncated = story_text[:500] + "..." if len(story_text) > 500 else story_text
            context_parts.append(f"Story excerpt: {truncated}")
        
        context = "\n".join(context_parts)
        
        response = await client.chat.completions.create(
            model=settings.openai.get("model", "gpt-4o-mini") if settings.openai else "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a social media expert who writes viral LinkedIn captions. 
Your task is to create a SHORT, curiosity-inducing caption for a video post.

Rules:
- Keep it under 150 characters (this is critical!)
- Create curiosity or intrigue - make people WANT to watch
- Use a conversational, authentic tone
- Avoid clickbait clichés like "You won't believe..."
- Can include 1-2 relevant emojis if appropriate
- Don't use hashtags (they can be added separately)
- Focus on the insight, lesson, or surprising element

Examples of good captions:
- "The two-pizza rule changed how we build teams forever. 🍕"
- "What if your biggest failure was actually your best teacher?"
- "3 words transformed our entire customer support approach."
- "She said no to a promotion. Here's why it was brilliant."
"""
                },
                {
                    "role": "user",
                    "content": f"Create a short, curiosity-inducing LinkedIn caption for this video:\n\n{context}"
                }
            ],
            max_tokens=100,
            temperature=0.8
        )
        
        caption = response.choices[0].message.content.strip()
        # Remove quotes if the model wrapped it in quotes
        if caption.startswith('"') and caption.endswith('"'):
            caption = caption[1:-1]
        
        logger.info(f"Generated LinkedIn caption: {caption}")
        return caption
        
    except Exception as e:
        logger.error(f"Error generating LinkedIn caption: {e}")
        # Fallback to simple caption
        return f"Check out this video: {story_title}" if story_title else "Check out my latest video!"


def get_linkedin_headers() -> dict:
    """Get headers for LinkedIn API requests."""
    return {
        "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }


def is_linkedin_configured() -> bool:
    """Check if LinkedIn credentials are configured."""
    return bool(settings.LINKEDIN_ACCESS_TOKEN and settings.LINKEDIN_MEMBER_URN)


async def register_upload(media_type: str) -> dict:
    """
    Register an upload with LinkedIn to get upload URL and asset URN.
    Step 1 of media upload process.
    
    Args:
        media_type: IMAGE, VIDEO, or DOCUMENT
        
    Returns:
        Dict with asset URN and upload URL
    """
    if not is_linkedin_configured():
        return {"success": False, "error": "LinkedIn credentials not configured"}
    
    try:
        url = f"{LINKEDIN_API_BASE}/assets?action=registerUpload"
        headers = get_linkedin_headers()
        
        # Determine recipe based on media type
        if media_type.upper() == "IMAGE":
            recipe = "urn:li:digitalmediaRecipe:feedshare-image"
        elif media_type.upper() == "VIDEO":
            recipe = "urn:li:digitalmediaRecipe:feedshare-video"
        elif media_type.upper() == "DOCUMENT":
            recipe = "urn:li:digitalmediaRecipe:feedshare-document"
        else:
            return {"success": False, "error": f"Unsupported media type: {media_type}"}
        
        payload = {
            "registerUploadRequest": {
                "recipes": [recipe],
                "owner": settings.LINKEDIN_MEMBER_URN,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ],
                "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
            }
        }
        
        logger.info(f"Registering {media_type} upload with LinkedIn...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    asset_urn = data["value"]["asset"]
                    upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                    return {
                        "success": True,
                        "asset": asset_urn,
                        "uploadUrl": upload_url
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Registration failed: HTTP {response.status}",
                        "message": error_text
                    }
    except Exception as e:
        logger.error(f"LinkedIn registration error: {e}")
        return {"success": False, "error": f"Registration error: {str(e)}"}


async def upload_media_from_url(upload_url: str, video_url: str) -> dict:
    """
    Download video from URL and upload to LinkedIn.
    Step 2 of media upload process.
    
    Args:
        upload_url: Upload URL from registration
        video_url: URL of the video to upload
        
    Returns:
        Dict with success status
    """
    try:
        logger.info(f"Downloading video from: {video_url}")
        
        async with aiohttp.ClientSession() as session:
            # Download the video
            async with session.get(video_url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"Failed to download video: HTTP {response.status}"
                    }
                
                video_data = await response.read()
                file_size = len(video_data)
                logger.info(f"Downloaded video: {file_size} bytes")
        
        # Determine timeout based on file size
        if file_size > 50 * 1024 * 1024:  # >50MB
            timeout = 600  # 10 minutes
        elif file_size > 10 * 1024 * 1024:  # >10MB
            timeout = 300  # 5 minutes
        else:
            timeout = 120  # 2 minutes
        
        logger.info(f"Uploading to LinkedIn with timeout: {timeout}s")
        
        upload_headers = {
            "Content-Type": "video/mp4",
            "Authorization": f"Bearer {settings.LINKEDIN_ACCESS_TOKEN}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.put(
                upload_url, 
                headers=upload_headers, 
                data=video_data,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status in [200, 201]:
                    logger.info("Video upload to LinkedIn successful!")
                    return {"success": True, "message": "Video uploaded successfully", "file_size": file_size}
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Upload failed: HTTP {response.status}",
                        "message": error_text
                    }
                    
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Upload timeout",
            "message": "The video upload took too long. Try a smaller file or check your connection."
        }
    except Exception as e:
        logger.error(f"LinkedIn upload error: {e}")
        return {"success": False, "error": f"Upload error: {str(e)}"}


async def create_linkedin_post(content: str, media_type: str = "TEXT", video_url: Optional[str] = None) -> dict:
    """
    Create a LinkedIn post with optional media (video).
    
    Args:
        content: Text content of the post
        media_type: Type of media - "TEXT" or "VIDEO"
        video_url: URL of video file (required for VIDEO type)
    
    Returns:
        Dict with success status and post URN or error details
    """
    if not is_linkedin_configured():
        return {
            "success": False,
            "error": "LinkedIn credentials not configured. Please add LINKEDIN_ACCESS_TOKEN and LINKEDIN_MEMBER_URN to your .env file."
        }
    
    media_type = media_type.strip().upper()
    logger.info(f"Creating LinkedIn {media_type} post: {content[:50]}...")
    
    # Validate inputs
    if media_type not in ["TEXT", "VIDEO"]:
        return {
            "success": False,
            "error": f"Invalid media_type: {media_type}. Must be TEXT or VIDEO"
        }
    
    if media_type == "VIDEO" and not video_url:
        return {
            "success": False,
            "error": "VIDEO posts require a video_url parameter"
        }
    
    # Step 1: Upload media if needed
    asset_urn = None
    if media_type == "VIDEO":
        logger.info("Step 1: Registering VIDEO upload...")
        register_result = await register_upload(media_type)
        
        if not register_result["success"]:
            return register_result
        
        asset_urn = register_result["asset"]
        upload_url = register_result["uploadUrl"]
        
        logger.info("Step 2: Uploading video file...")
        upload_result = await upload_media_from_url(upload_url, video_url)
        
        if not upload_result["success"]:
            return upload_result
        
        logger.info(f"Video uploaded successfully! Asset URN: {asset_urn}")
        
        # Wait for video processing
        file_size_mb = upload_result.get("file_size", 10 * 1024 * 1024) / (1024 * 1024)
        wait_time = min(120, max(30, int(file_size_mb * 2)))  # 2 seconds per MB, 30-120 seconds
        logger.info(f"Waiting for LinkedIn video processing ({wait_time} seconds)...")
        await asyncio.sleep(wait_time)
    
    # Step 3: Create the post
    url = f"{LINKEDIN_API_BASE}/ugcPosts"
    headers = get_linkedin_headers()
    
    # Build payload based on media type
    if media_type == "TEXT":
        payload = {
            "author": settings.LINKEDIN_MEMBER_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    elif media_type == "VIDEO":
        payload = {
            "author": settings.LINKEDIN_MEMBER_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "VIDEO",
                    "media": [
                        {
                            "status": "READY",
                            "media": asset_urn
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
    
    logger.info("Step 3: Creating LinkedIn post...")
    
    # Use longer timeout for video posts
    post_timeout = 600 if media_type == "VIDEO" else 30
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=aiohttp.ClientTimeout(total=post_timeout)
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    post_urn = data.get("id")
                    logger.info(f"LinkedIn post created successfully! URN: {post_urn}")
                    return {
                        "success": True,
                        "post_urn": post_urn,
                        "asset_urn": asset_urn,
                        "message": "Post created successfully on LinkedIn"
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"LinkedIn post creation failed: HTTP {response.status} - {error_text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "message": error_text,
                        "status_code": response.status
                    }
    except asyncio.TimeoutError:
        # For video posts, timeout may not mean failure
        return {
            "success": False,
            "error": "Post creation timeout",
            "message": "The post creation took too long. If posting a video, check your LinkedIn profile - the post may still have been created successfully."
        }
    except Exception as e:
        logger.error(f"LinkedIn post creation error: {e}")
        return {"success": False, "error": f"Post creation error: {str(e)}"}
