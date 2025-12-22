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
        # Model configuration for different tasks
        self.character_model = "gpt-4o-mini"
        self.video_prompt_model = "gpt-4o-mini"
        self.storyboard_model = "gpt-4o"

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
            - For ethnicity: Unless the story explicitly specifies otherwise, create a diverse mix with the following distribution: 60% white (Caucasian), 30% Black (African American), 10% other ethnicities.
            - For gender: Unless the story specifies, create a balanced mix of male and female characters, with a slight preference for male characters in professional/business contexts.
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

        response = await call_openai_api(self.client, messages, model=self.character_model)
        if not response:
            logger.error("API returned empty response")
            return []
        
        logger.info(f"Character generation response: {response[:500]}...")  # Log first 500 chars
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # if the direct parsing fails, try to extract the JSON array part
            array_match = re.search(r'\[.*\]', response, re.DOTALL)
            if array_match:
                try:
                    return json.loads(array_match.group())
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse the response as a JSON array. Response: {response}")
                    return []
            else:
                logger.error(f"No JSON array found in the response. Response: {response}")
                return []

    async def generate_video_prompt(self, scene_description: str, art_style: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a Seadance 1.0 video generation request based on an image scene description.
        Returns a complete JSON request for video generation from the image.
        """
        prompt = f"""Based on this image scene description, create a SIMPLE, MINIMAL video motion prompt for Seadance 1.0 video generation.

Scene Description: {scene_description}
Art Style: {art_style if art_style else 'photorealistic'}

Create a brief video prompt with MINIMAL motion description. Keep it simple:
- Use general terms, not specific detailed actions
- Keep movements slow and subtle
- Avoid complex or exaggerated motion
- Focus on gentle, natural movement only

The motion should be:
- MINIMAL and understated
- Slow and smooth
- Simple and conservative
- Natural but NOT detailed

Generate a complete Seadance 1.0 API request in JSON format with these fields:
- prompt: BRIEF motion description (keep it general and simple - avoid specific detailed actions)
- negative_prompt: What to avoid in the video
- num_inference_steps: Recommended inference steps (default: 50)
- guidance_scale: Recommended guidance scale (default: 7.5)
- duration: Video duration in seconds (default: 5)
- fps: Frames per second (default: 24)

Return ONLY the JSON object, no other text."""

        messages = [
            {
                "role": "system",
                "content": """You are an expert in video generation. You specialize in creating SIMPLE, MINIMAL motion prompts.
                
                CRITICAL RULES:
                1. Keep motion descriptions SHORT and GENERAL
                2. Use broad terms like "gentle movement" instead of specific detailed actions
                3. Avoid describing complex or specific human movements
                4. Prioritize subtlety over detail
                5. When in doubt, use less description
                
                You create simple, understated motion descriptions that avoid unintended distortions."""
            },
            {"role": "user", "content": prompt},
        ]

        response = await call_openai_api(self.client, messages, model=self.video_prompt_model)
        if not response:
            logger.error("API returned empty response for video prompt")
            return self._create_default_video_request()
        
        # Find the JSON part of the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                video_request = json.loads(json_str)
                return video_request
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error in video prompt: {e}")
                return self._create_default_video_request()
        else:
            logger.error("No JSON object found in video prompt response")
            return self._create_default_video_request()
    
    def _create_default_video_request(self) -> Dict[str, Any]:
        """Create a default video generation request when AI generation fails"""
        return {
            "prompt": "Subtle camera movement, natural ambient motion",
            "negative_prompt": "static, frozen, jerky motion, unnatural movement",
            "num_inference_steps": 50,
            "guidance_scale": 7.5,
            "duration": 5,
            "fps": 24
        }

    async def generate_storyboard(self, title: str, story: str, character_names: List[str], tweak_prompt: Optional[str] = None, art_style: Optional[str] = None) -> Dict[str, Any]:
        """Generate storyboard from custom story - universal method"""
        max_scenes = self.config.storyboard.get('max_scenes', 30)
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        
        # Add tweak prompt guidance if provided
        tweak_guidance = ""
        if tweak_prompt:
            tweak_guidance = f"\n\nAdditional Visual Guidance: {tweak_prompt}\nApply this guidance to the visual descriptions, camera work, and lighting choices throughout all scenes."
        
        # Add art style guidance - always enforce the art style
        art_style_guidance = f"\n\nArt Style: {art_style if art_style else 'photorealistic'}\nCRITICAL: ALL scene descriptions MUST be appropriate for and explicitly reference this {art_style if art_style else 'photorealistic'} art style. Every visual element should be described in a way that clearly conveys this artistic treatment."
        
        prompt = f"""Based on the following custom story, create a detailed storyboard with up to {max_scenes} scenes.

            Story Title: {title}
            Character Names: {', '.join(character_names) if character_names else 'No specific characters'}
            {tweak_guidance}
            {art_style_guidance}

            IMPORTANT TERMINOLOGY RULES:
            - NEVER use the words "animate", "animated", "animation", "stylized", "illustration", "illustrated", or "depicted" in your descriptions
            - Instead, rely on the specified art style to convey non-realistic character styles
            - Use terms like "rendered", "portrayed", or "designed"
            - For character descriptions, focus on visual appearance, not animation state
            - Example: Instead of "animated character", "stylized character", "illustrated character", or "depicted character", use "{art_style if art_style else 'rendered'} character"

            First, create an opening scene:
            1. Scene Number: 1
            2. Description: A vivid description (60-70 words) that sets up an engaging hook related to the story. 
            3. Subtitles: An engaging question or statement that captures the essence of the story.
            4. Camera, Lighting, and Transition: As per the guidelines below.

            Then, for each subsequent scene, provide the following details:
            1. Scene Number: An integer starting from 1 and incrementing sequentially (1, 2, 3, etc.)
            2. Description: A vivid description (60-70 words) focusing on key visual elements.
            3. Subtitles: Use EXACT quotes from the original story WITH ALL PUNCTUATION PRESERVED (periods, commas, question marks, exclamation points, etc.)
            4. Camera: Specify the angle, composition type, and shot size.
            5. Lighting: Describe the lighting type used.
            6. Transition: Specify the type of transition to the current scene.

            Guidelines:
            - Scene numbers MUST be integers (1, 2, 3, etc.), NOT strings.
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
            - CRITICAL: Every scene description MUST explicitly incorporate the {art_style if art_style else 'photorealistic'} art style
            - Describe all visual elements in a way that clearly conveys the {art_style if art_style else 'photorealistic'} artistic treatment
            - NEVER use "animate", "animated", "animation", "stylized", "illustration", or "illustrated" - use alternative descriptive terms

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
                        "scene_number": 1,
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
                    10. ALWAYS ensuring every scene description explicitly reflects the {art_style if art_style else 'photorealistic'} art style
                    11. Describing all visual elements in ways that clearly convey the artistic treatment

                    CRITICAL: You NEVER use the words "animate", "animated", "animation", "stylized", "illustration", or "illustrated" in your descriptions.
                    Instead, you use terms like "rendered", "depicted", "portrayed", or "designed".
                    The art style specification handles the visual treatment - you focus on describing what is seen in that {art_style if art_style else 'photorealistic'} style.

                    Your storyboards effectively bridge the gap between written narrative and visual representation, 
                    working seamlessly with any story type, genre, or art style.'''
            },
            {"role": "user", "content": prompt},
        ]

        response = await call_openai_api(self.client, messages, model=self.storyboard_model)
        if not response:
            logger.error("API returned empty response")
            return create_empty_storyboard(title)
        
        # Find the JSON part of the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                storyboard_data = json.loads(json_str)
                
                # Validate and normalize scene_number field
                if storyboard_data.get("storyboards"):
                    for idx, scene in enumerate(storyboard_data["storyboards"]):
                        # Ensure scene_number exists and is an integer
                        if "scene_number" not in scene or not isinstance(scene["scene_number"], int):
                            scene["scene_number"] = idx + 1
                            logger.warning(f"Scene {idx} missing or invalid scene_number, set to {idx + 1}")
                
                # Generate video prompts for select key scenes only (first, two middle, last)
                logger.info("Generating video prompts for key scenes...")
                if storyboard_data.get("storyboards"):
                    scenes = storyboard_data["storyboards"]
                    total_scenes = len(scenes)
                    
                    # Determine which scenes to generate prompts for
                    key_scene_indices = set()
                    if total_scenes > 0:
                        key_scene_indices.add(0)  # First scene
                    if total_scenes > 3:
                        # Two scenes near the middle
                        mid_point = total_scenes // 2
                        key_scene_indices.add(mid_point - 1)
                        key_scene_indices.add(mid_point)
                    if total_scenes > 1:
                        key_scene_indices.add(total_scenes - 1)  # Last scene
                    
                    for idx, scene in enumerate(scenes):
                        if idx in key_scene_indices:
                            scene_description = scene.get("description", "")
                            try:
                                if scene_description:
                                    logger.info(f"Generating video prompt for scene {scene.get('scene_number', idx + 1)} (key scene)")
                                    video_request = await self.generate_video_prompt(scene_description, art_style)
                                    scene["video_generation_request"] = video_request
                                else:
                                    scene["video_generation_request"] = self._create_default_video_request()
                            except Exception as e:
                                logger.warning(f"Failed to generate video prompt for scene {scene.get('scene_number', idx + 1)}: {e}")
                                scene["video_generation_request"] = self._create_default_video_request()
                        # No video prompt for non-key scenes
                
                return storyboard_data
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error: {e}")
                logger.error(f"Failed to parse JSON: {json_str}")
                return create_empty_storyboard(title)
        else:
            logger.error("No JSON object found in the response")
            logger.error(f"Full response: {response}")
            return create_empty_storyboard(title)


