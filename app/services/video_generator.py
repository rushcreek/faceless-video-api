import os
import asyncio
from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeVideoClip,
    ColorClip
)
from app.services.audio_generator import AudioGenerator
from app.utils.transitions import zoom 
import shortcap
from app.core.config import settings
from app.core.logging import logger
from app.utils.image_utils import download_image
from PIL import Image

class VideoGenerator:
    def __init__(self, client=None):
        # client parameter kept for backward compatibility but not used with Cartesia
        self.audio_generator = AudioGenerator()
        self.font_path = os.path.join(settings.BASE_DIR, "resources/fonts")
        self.assets_path = os.path.join(os.path.dirname(settings.BASE_DIR), "assets")
    
    def create_closing_screen(self, duration=4):
        """Create a closing screen with two logos on black background with fade-in effect"""
        try:
            # Load the logo images
            prlogo_path = os.path.join(self.assets_path, "prlogo.png")
            appstore_path = os.path.join(self.assets_path, "appstore.png")
            
            # Open images with PIL to get dimensions
            prlogo_img = Image.open(prlogo_path)
            appstore_img = Image.open(appstore_path)
            
            # Video dimensions (9:16 aspect ratio)
            video_width = 1080
            video_height = 1920
            
            # Calculate scaling to fit nicely with padding
            # Leave 20% padding on each side (60% of width for logos)
            max_logo_width = int(video_width * 0.6)
            
            # Scale prlogo
            prlogo_aspect = prlogo_img.width / prlogo_img.height
            prlogo_width = max_logo_width
            prlogo_height = int(prlogo_width / prlogo_aspect)
            
            # Scale appstore (usually wider, keep it proportional)
            appstore_aspect = appstore_img.width / appstore_img.height
            appstore_width = max_logo_width
            appstore_height = int(appstore_width / appstore_aspect)
            
            # Create black background
            background = ColorClip(size=(video_width, video_height), color=(0, 0, 0), duration=duration)
            
            # Vertical spacing between logos
            spacing = 60
            
            # Calculate vertical positioning to center both logos together
            total_height = prlogo_height + spacing + appstore_height
            start_y = (video_height - total_height) // 2
            
            # Create logo clips
            prlogo_clip = (ImageClip(prlogo_path)
                          .resize(width=prlogo_width)
                          .set_duration(duration)
                          .set_position(('center', start_y))
                          .fadein(0.5))
            
            appstore_clip = (ImageClip(appstore_path)
                            .resize(width=appstore_width)
                            .set_duration(duration)
                            .set_position(('center', start_y + prlogo_height + spacing))
                            .fadein(0.5))
            
            # Composite all elements
            closing_screen = CompositeVideoClip([background, prlogo_clip, appstore_clip])
            
            return closing_screen
            
        except Exception as e:
            logger.error(f"Error creating closing screen: {str(e)}")
            return None

    async def add_captions(self, output_file, output_file_subtitle):
        shortcap.add_captions(
            video_file=output_file,
            output_file=output_file_subtitle,
            font=os.path.join(self.font_path, "TitanOne.ttf"),
            font_size=70,
            font_color="white",
            stroke_width=3,
            stroke_color="black",
            shadow_strength=1.0,
            shadow_blur=0.1,
            highlight_current_word=True,
            word_highlight_color="yellow",
            line_count=1,
            padding=70,
            position="bottom",
            use_local_whisper=False,
        )

    async def generate_video(self, storyboard_project, story_dir, voice_name):
        audio_dir = os.path.join(story_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        video_path = os.path.join(story_dir, "story_video.mp4")
        clips = []
        try:
            for scene in storyboard_project['storyboards']:
                # Generate audio for the subtitle
                audio_file = os.path.join(audio_dir, f"scene_{scene['scene_number']}.mp3")
                success = await self.audio_generator.generate_audio(scene['subtitles'], audio_file, voice_name)
                if not success:
                    logger.error(f"Failed to generate audio for scene {scene['scene_number']}")
                    continue

                # Create audio clip
                audio_clip = AudioFileClip(audio_file)
                
                # Download and use the image
                image_path = os.path.join(story_dir, f"scene_{scene['scene_number']}.png")
                downloaded_image = await download_image(scene['image'], image_path)
                
                if downloaded_image is None:
                    logger.error(f"Skipping scene {scene['scene_number']} due to image download failure")
                    continue
                
                # Create image clip with duration matching the audio
                image_clip = ImageClip(downloaded_image).set_duration(audio_clip.duration)
                
                # Combine image, text, and audio
                video_clip = image_clip.set_audio(audio_clip)

                # Apply transition effect
                transition_type = scene['transition_type']
                    
                if transition_type == 'zoom-in':
                    clips.append(zoom(video_clip))
                elif transition_type == 'zoom-out':
                    clips.append(zoom(video_clip, mode='out'))
                else:
                    clips.append(video_clip)

            if not clips:
                logger.error("No valid clips generated")
                return None

            # Add closing screen
            closing_screen = self.create_closing_screen(duration=4)
            if closing_screen:
                clips.append(closing_screen)
                logger.info("Added closing screen with logos to video")
            
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Use a separate thread for video writing to avoid blocking the event loop
            await asyncio.to_thread(
                final_clip.write_videofile,
                video_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                audio_bitrate='192k',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                preset='medium',
                threads=4
            )

            subtitle_video_path = video_path.replace('.mp4', '_subtitle.mp4')
            await self.add_captions(video_path, subtitle_video_path)

            return subtitle_video_path
        except Exception as e:
            logger.error(f"Error in generate_video: {str(e)}")
            return None
