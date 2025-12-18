import os
import re
from datetime import datetime
from typing import Dict, Any, Tuple
from PIL import Image
from app.core.logging import logger
from app.core.config import settings


def create_resource_dir(base_dir: str, story_type: str, title: str) -> str:
    # Remove leading/trailing spaces and quotes, then replace special characters and spaces
    clean_title = re.sub(r'[-\s]+', '_', re.sub(r'[^\w\s-]', '', title.strip().strip('"')))

    # Create a directory for the story type
    story_type_dir = os.path.join(base_dir, story_type)
    os.makedirs(story_type_dir, exist_ok=True)

    # Create a directory for this story
    story_dir = os.path.join(story_type_dir, clean_title)
    os.makedirs(story_dir, exist_ok=True)

    return story_dir

async def call_openai_api(client, messages, model=None, max_retries=3, timeout=120):
    import asyncio
    
    # Use provided model or fall back to settings default
    selected_model = model if model is not None else settings.openai.get('model')
    
    for attempt in range(max_retries):
        try:
            # Add timeout to prevent hanging indefinitely
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=selected_model,
                    temperature=settings.openai.get('temperature'),
                    messages=messages,
                    timeout=timeout  # Client-side timeout
                ),
                timeout=timeout + 10  # Additional buffer for async wrapper
            )
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            logger.error(f"OpenAI API timeout after {timeout}s (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed due to timeout")
                return None
            wait_time = 2 ** attempt
            logger.info(f"Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error calling OpenAI API (attempt {attempt + 1}/{max_retries}): {e}")
            
            # If this was the last attempt, return None
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed")
                return None
            
            # Wait with exponential backoff before retrying
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.info(f"Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)

def create_empty_storyboard(title: str) -> Dict[str, Any]:
    return {
        "project_info": {
            "title": title,
            "user": "AI Generated",
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        },
        "storyboards": []
    }

def create_blank_image(filename, width=720, height=1280):
    blank_image = Image.new('RGB', (width, height), color='black')
    blank_image.save(filename)
    logger.info(f"Created blank image: {filename}")

def get_story_limit(duration: str) -> Tuple[int, int]:
    if duration == "short":
        return (settings.story_limit_short.get('char_limit_min', 700), settings.story_limit_short.get('char_limit_max', 800))
    elif duration == "long":
        return (settings.story_limit_long.get('char_limit_min', 900), settings.story_limit_long.get('char_limit_max', 1000))
    else:
        raise ValueError(f"Invalid duration: {duration}")