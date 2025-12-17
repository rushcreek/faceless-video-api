# app/services/story_generator.py
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import re
from app.utils.helpers import call_openai_api, create_empty_storyboard
from app.core.config import settings
from app.core.logging import logger


class StoryGenerator:
    def __init__(self, client):
        self.client = client
        self.config = settings

    async def generate_characters(self, story: str) -> List[Dict[str, str]]:
        prompt = f"""Based on the following story, create detailed descriptions for each character, including their name, ethnicity, gender, age, facial features, body type, hair style, and accessories. Focus on permanent or long-term attributes.

            Story:
            {story}

            Output format:
            [
                {{
                    "name": "Character Name",
                    "ethnicity": "Character's Ethnicity",
                    "gender": "Character's Gender",
                    "age": "Character's Age",
                    "facial_features": "Description of Character's facial features",
                    "body_type": "Description of Character's body type",
                    "hair_style": "Description of Character's hair style",
                    "accessories": "Description of Character's accessories"
                }},
                ...
            ]

            Guidelines:
            - Include the character's name as it appears in the story.
            - Specify the character's ethnicity if it's relevant and discernible from the story.
            - State the character's gender.
            - Specify the character's age or apparent age range.
            - For facial features, include details about eyes, nose, mouth, chin, forehead, cheekbones, and overall face shape. Include any notable unique features like scars, birthmarks, or facial hair.
            - Describe the character's body type, including height and build.
            - For hair style, describe the color, length, style, and texture.
            - For accessories, include only non-clothing items such as jewelry, glasses and watches that are consistently associated with the character.
            - Aim for concise but descriptive entries for each attribute.
            - Focus on permanent or long-term features, not on changeable expressions or temporary states.
            - Do not include any descriptions of clothing or attire.

            Please provide only the JSON array, without any additional text.
            """

        messages = [
            {
                "role": "system",
                "content": """You are an expert at analyzing stories and creating detailed, vivid character descriptions, focusing on overall appearance. Your skills include:
                    1. Extracting subtle character details from narrative context
                    2. Creating consistent and believable descriptions of characters
                    3. Focusing on permanent features and distinguishing attributes
                    4. Adapting descriptions to fit the story's genre and tone
                    5. Balancing physical features with character essence
                    6. Translating character personalities into comprehensive physical attributes
                    7. Accurately estimating and describing characters' attributes based on story context
                    8. Avoiding any mention of clothing or attire in character descriptions"""
            }, 
            {"role": "user", "content": prompt},
        ]

        response = await call_openai_api(self.client, messages)
        if not response:
            logger.error("API returned empty response")
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # if the direct parsing fails, try to extract the JSON array part
            array_match = re.search(r'\[.*\]', response, re.DOTALL)
            if array_match:
                try:
                    return json.loads(array_match.group())
                except json.JSONDecodeError:
                    logger.error("Failed to parse the response as a JSON array.")
                    return []
            else:
                logger.error("No JSON array found in the response.")
                return []

    async def generate_storyboard(self, title: str, story: str, character_names: List[str], tweak_prompt: Optional[str] = None, art_style: Optional[str] = None) -> Dict[str, Any]:
        """Generate storyboard from custom story - universal method"""
        max_scenes = self.config.storyboard.get('max_scenes', 30)
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        
        # Add tweak prompt guidance if provided
        tweak_guidance = ""
        if tweak_prompt:
            tweak_guidance = f"\n\nAdditional Visual Guidance: {tweak_prompt}\nApply this guidance to the visual descriptions, camera work, and lighting choices throughout all scenes."
        
        # Add art style guidance if provided
        art_style_guidance = ""
        if art_style:
            art_style_guidance = f"\n\nArt Style: {art_style}\nEnsure all scene descriptions are appropriate for this art style."
        
        prompt = f"""Based on the following custom story, create a detailed storyboard with up to {max_scenes} scenes.

            Story Title: {title}
            Character Names: {', '.join(character_names) if character_names else 'No specific characters'}
            {tweak_guidance}
            {art_style_guidance}

            IMPORTANT TERMINOLOGY RULES:
            - NEVER use the words "animate", "animated", "animation", or "stylized" in your descriptions
            - Instead, rely on the specified art style to convey non-realistic character styles
            - Use terms like "illustrated", "rendered", "depicted", "portrayed", or "designed"
            - For character descriptions, focus on visual appearance, not animation state
            - Example: Instead of "animated character" or "stylized character", use "illustrated character" or "{art_style if art_style else 'rendered'} character"

            First, create an opening scene:
            1. Scene Number: 1
            2. Description: A vivid description (60-70 words) that sets up an engaging hook related to the story. 
            3. Subtitles: An engaging question or statement that captures the essence of the story.
            4. Camera, Lighting, and Transition: As per the guidelines below.

            Then, for each subsequent scene, provide the following details:
            1. Scene Number
            2. Description: A vivid description (60-70 words) focusing on key visual elements.
            3. Subtitles: Use EXACT quotes from the original story WITH ALL PUNCTUATION PRESERVED (periods, commas, question marks, exclamation points, etc.)
            4. Camera: Specify the angle, composition type, and shot size.
            5. Lighting: Describe the lighting type used.
            6. Transition: Specify the type of transition to the current scene.

            Guidelines:
            - Subtitles MUST contain only exact text from the original story, without any additions, omissions, or modifications.
            - PRESERVE ALL PUNCTUATION exactly as it appears in the original story (periods, commas, question marks, exclamation points, quotation marks, apostrophes, dashes, etc.)
            - Include every sentence from the original story in the subtitles, maintaining the correct order across all scenes.
            - Each subtitle must be unique; do not repeat content in multiple scenes.
            - For partial sentences at scene boundaries, include the fragment and continue it in the next scene's subtitles.
            - EVERY SCENE MUST HAVE NON-EMPTY SUBTITLES. If you run out of story text, do not create additional scenes.
            - Select scenes that represent pivotal moments or significant changes in the story.
            - Ensure that the scenes flow logically and capture the essence of the story.
            - Describe characters' clothing and appearance in detail, ensuring consistency.
            - The total number of scenes should not exceed {max_scenes}.
            - When using a character's name in possessive form (e.g., "Character's") in the description, 
              surround it with double curly braces {{{{{{{{ }}}}}}}} if it's not referring to the character's appearance.
            {f"- Apply the visual guidance throughout: {tweak_prompt}" if tweak_prompt else ""}
            {f"- Ensure all descriptions match the {art_style} art style" if art_style else ""}
            - NEVER use "animate", "animated", "animation", or "stylized" - use alternative descriptive terms

            Use only the following options for camera, lighting, and transition details:
            - Camera angles: low angle, high angle, Dutch angle, bird's eye view, worm's eye view, eye level, canted angle
            - Composition types: single shot, two-shot, over-the-shoulder, insert shot, establishing shot
            - Shot sizes: extreme close-up, close-up, medium shot, full body shot, long shot, wide shot, extreme long shot
            - Lighting types: three-point lighting, high-key lighting, low-key lighting, natural lighting, practical lighting, motivated lighting, rim lighting, soft lighting, hard lighting, silhouette lighting
            - Transition types: zoom-in, zoom-out

            Important rules:
            1. Do not use zoom-in transitions when the current scene's shot size is close-up or extreme close-up.
            2. Logical consistency: Ensure camera, lighting, and composition choices match the scene content.
            3. For transitions, use ONLY zoom-in or zoom-out.

            Output the result as a JSON object with the following structure:
            {{{{
                "project_info": {{{{
                    "title": "{title}",
                    "user": "AI Generated",
                    "timestamp": "{timestamp}"
                }}}},
                "storyboards": [
                    {{{{
                        "scene_number": "Scene Number",
                        "description": "Scene Description",
                        "subtitles": "Subtitles or Dialogue",
                        "image": null,
                        "camera": {{{{
                            "angle": "Camera Angle",
                            "composition_type": "Composition Type",
                            "shot_size": "Shot Size"
                        }}}},
                        "lighting": "Lighting Type",
                        "transition_type": "Transition Type"
                    }}}},
                    ...
                ]
            }}}}

            Here's the story:

        {story}"""

        messages = [
            {
                "role": "system",
                "content": f'''You are a highly skilled storyboard artist with expertise in visual storytelling across all genres. You excel at:
                    1. Creating vivid, cinematic scene descriptions for any type of narrative
                    2. Adapting to various story styles and art styles while maintaining the original narrative's essence
                    3. Incorporating cinematographic techniques into your descriptions
                    4. Faithfully representing the original story using exact quotes for subtitles
                    5. Ensuring visual narrative accurately captures key moments, emotions, and atmosphere
                    6. Describing characters and settings in detail with consistency
                    7. Specifying appropriate camera angles, compositions, shot sizes, and lighting
                    8. Maintaining logical consistency between scene content and technical descriptions
                    {"9. Applying creative visual guidance while preserving story integrity" if tweak_prompt else ""}
                    {"10. Ensuring all descriptions match the " + art_style + " art style" if art_style else ""}

                    CRITICAL: You NEVER use the words "animate", "animated", "animation", or "stylized" in your descriptions.
                    Instead, you use terms like "illustrated", "rendered", "depicted", "portrayed", or "designed".
                    The art style specification handles the visual treatment - you focus on describing what is seen.

                    Your storyboards effectively bridge the gap between written narrative and visual representation, 
                    working seamlessly with any story type, genre, or art style.'''
            },
            {"role": "user", "content": prompt},
        ]

        response = await call_openai_api(self.client, messages)
        if not response:
            logger.error("API returned empty response")
            return create_empty_storyboard(title)
        
        # Find the JSON part of the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                storyboard_data = json.loads(json_str)
                return storyboard_data
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error: {e}")
                logger.error(f"Failed to parse JSON: {json_str}")
                return create_empty_storyboard(title)
        else:
            logger.error("No JSON object found in the response")
            logger.error(f"Full response: {response}")
            return create_empty_storyboard(title)


