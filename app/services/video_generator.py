import os
import asyncio
import time
from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeVideoClip,
    ColorClip,
    AudioClip,
    TextClip
)
from app.services.audio_generator import AudioGenerator
from app.utils.transitions import zoom 
import shortcap
from app.core.config import settings
from app.core.logging import logger
from app.utils.image_utils import download_image
from PIL import Image
import json
import openai
from difflib import SequenceMatcher

class VideoGenerator:
    def __init__(self, client=None):
        # client parameter kept for backward compatibility but not used with Cartesia
        self.audio_generator = AudioGenerator()
        self.font_path = os.path.join(settings.BASE_DIR, "resources/fonts")
        self.assets_path = os.path.join(os.path.dirname(settings.BASE_DIR), "assets")
    
    def align_script_with_transcription(self, original_text, transcription_words):
        """
        Align original script words (with punctuation) to Whisper transcription words (with timing).
        Returns words from original script with timing from transcription.
        """
        # Clean words for matching (remove punctuation, lowercase)
        import re
        
        def clean_word(word):
            return re.sub(r'[^\w\s]', '', word.lower()).strip()
        
        # Split original text into words, preserving original form
        original_words = original_text.split()
        
        # Extract clean transcription words
        transcribed_clean = [clean_word(w['word']) for w in transcription_words]
        original_clean = [clean_word(w) for w in original_words]
        
        # Use sequence matcher to align
        matcher = SequenceMatcher(None, original_clean, transcribed_clean)
        aligned_words = []
        
        orig_idx = 0
        trans_idx = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Words match - use original word with transcription timing
                for i, orig_i in enumerate(range(i1, i2)):
                    trans_i = j1 + i
                    if trans_i < len(transcription_words):
                        aligned_words.append({
                            "word": " " + original_words[orig_i],  # Keep original with punctuation
                            "start": transcription_words[trans_i]['start'],
                            "end": transcription_words[trans_i]['end']
                        })
            elif tag == 'replace':
                # Words differ - try to map best we can
                orig_chunk = original_words[i1:i2]
                trans_chunk = transcription_words[j1:j2]
                
                # If same length, map 1:1
                if len(orig_chunk) == len(trans_chunk):
                    for orig_word, trans_word in zip(orig_chunk, trans_chunk):
                        aligned_words.append({
                            "word": " " + orig_word,
                            "start": trans_word['start'],
                            "end": trans_word['end']
                        })
                else:
                    # Different lengths - distribute timing evenly
                    if trans_chunk:
                        start_time = trans_chunk[0]['start']
                        end_time = trans_chunk[-1]['end']
                        duration = end_time - start_time
                        word_duration = duration / len(orig_chunk) if orig_chunk else 0
                        
                        for i, orig_word in enumerate(orig_chunk):
                            aligned_words.append({
                                "word": " " + orig_word,
                                "start": start_time + (i * word_duration),
                                "end": start_time + ((i + 1) * word_duration)
                            })
            elif tag == 'delete':
                # Word in original but not transcription - estimate timing
                if aligned_words:
                    last_end = aligned_words[-1]['end']
                    word_duration = 0.3  # Default duration
                    for orig_i in range(i1, i2):
                        aligned_words.append({
                            "word": " " + original_words[orig_i],
                            "start": last_end,
                            "end": last_end + word_duration
                        })
                        last_end += word_duration
            elif tag == 'insert':
                # Word in transcription but not original - skip it
                pass
        
        return aligned_words
    
    async def transcribe_audio_with_whisper(self, audio_file):
        """
        Transcribe audio file using OpenAI Whisper API to get accurate word-level timing.
        """
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info(f"Transcribing audio file: {audio_file}")
            
            with open(audio_file, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            # Extract word-level timing
            words = []
            if hasattr(transcript, 'words') and transcript.words:
                for word in transcript.words:
                    words.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end
                    })
            
            logger.info(f"Transcription complete: {len(words)} words extracted")
            return words
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return None
    
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
            
            # Create logo clips with transparency support
            prlogo_clip = (ImageClip(prlogo_path, transparent=True)
                          .resize(width=prlogo_width)
                          .set_duration(duration)
                          .set_position(('center', start_y))
                          .fadein(0.5))
            
            appstore_clip = (ImageClip(appstore_path, transparent=True)
                            .resize(width=appstore_width)
                            .set_duration(duration)
                            .set_position(('center', start_y + prlogo_height + spacing))
                            .fadein(0.5))
            
            # Composite all elements
            closing_screen = CompositeVideoClip([background, prlogo_clip, appstore_clip])
            
            # Add silent audio to prevent audio glitches when concatenating
            # Create silent audio clip matching the duration
            def make_frame(t):
                return 0  # Silent audio (zero amplitude)
            
            silent_audio = AudioClip(make_frame, duration=duration, fps=44100)
            closing_screen = closing_screen.set_audio(silent_audio)
            
            return closing_screen
            
        except Exception as e:
            logger.error(f"Error creating closing screen: {str(e)}")
            return None

    async def add_captions(self, output_file, output_file_subtitle, caption_font='BebasNeue', custom_segments=None):
        """Add phrase-based captions to video with punctuation preserved from storyboard"""
        shortcap.add_captions(
            video_file=output_file,
            output_file=output_file_subtitle,
            font=os.path.join(self.font_path, f"{caption_font}.ttf"),
            font_size=92,
            font_color="white",
            stroke_width=3,
            stroke_color="black",
            shadow_strength=1.0,
            shadow_blur=0.1,
            highlight_current_word=True,
            word_highlight_color="yellow",
            line_count=2,  # Show 2-3 lines to display more words as phrases
            segments=custom_segments,  # Pass custom segments to preserve punctuation
            use_local_whisper=False,
        )

    async def generate_video(self, storyboard_project, story_dir, voice_name, caption_font='BebasNeue', progress_callback=None):
        audio_dir = os.path.join(story_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        video_path = os.path.join(story_dir, "story_video.mp4")
        clips = []
        
        # Timing profiling
        timings = {}
        start_total = time.time()
        
        # Store subtitle timing info for custom caption segments
        subtitle_segments = []
        current_time = 0.0
        
        try:
            # Audio generation phase
            start_audio = time.time()
            for scene in storyboard_project['storyboards']:
                # Generate audio for the subtitle
                audio_file = os.path.join(audio_dir, f"scene_{scene['scene_number']}.mp3")
                success = await self.audio_generator.generate_audio(scene['subtitles'], audio_file, voice_name)
                if not success:
                    logger.error(f"Failed to generate audio for scene {scene['scene_number']}")
                    continue

                # Create audio clip to get duration
                audio_clip = AudioFileClip(audio_file)
                duration = audio_clip.duration
                
                # Transcribe audio with Whisper to get accurate word-level timing
                logger.info(f"Transcribing scene {scene['scene_number']} for accurate timing...")
                transcription_words = await self.transcribe_audio_with_whisper(audio_file)
                
                word_segments = []
                if transcription_words:
                    # Align original script words (with punctuation) to transcription timing
                    logger.info(f"Aligning script with transcription for scene {scene['scene_number']}...")
                    aligned_words = self.align_script_with_transcription(
                        scene['subtitles'], 
                        transcription_words
                    )
                    
                    # Adjust timing to account for current_time offset
                    for word in aligned_words:
                        word_segments.append({
                            "word": word["word"],
                            "start": current_time + word["start"],
                            "end": current_time + word["end"]
                        })
                else:
                    # Fallback to simple timing if transcription fails
                    logger.warning(f"Transcription failed for scene {scene['scene_number']}, using fallback timing")
                    words = scene['subtitles'].split()
                    if words:
                        word_duration = duration / len(words)
                        for i, word in enumerate(words):
                            word_start = current_time + (i * word_duration)
                            word_end = word_start + word_duration
                            word_segments.append({
                                "word": " " + word,
                                "start": word_start,
                                "end": word_end
                            })
                
                subtitle_segments.append({
                    "start": current_time,
                    "end": current_time + duration,
                    "words": word_segments
                })
                
                current_time += duration
                audio_clip.close()
            
            timings['audio_generation'] = time.time() - start_audio
            
            # Report progress after audio/transcription phase (50-60%)
            if progress_callback:
                await progress_callback(0.91, "Processing clips...")
            
            # Image processing and clip creation phase
            start_clips = time.time()
            for scene in storyboard_project['storyboards']:
                audio_file = os.path.join(audio_dir, f"scene_{scene['scene_number']}.mp3")
                if not os.path.exists(audio_file):
                    continue
                audio_clip = AudioFileClip(audio_file)
                
                # Download and use the image - detect extension from URL
                image_url = scene['image']
                image_ext = '.jpg' if image_url.endswith('.jpg') else '.png'
                image_path = os.path.join(story_dir, f"scene_{scene['scene_number']}{image_ext}")
                downloaded_image = await download_image(image_url, image_path)
                
                if downloaded_image is None:
                    logger.error(f"Skipping scene {scene['scene_number']} due to image download failure")
                    continue
                
                # Validate the downloaded image file exists and has content
                if not os.path.exists(downloaded_image) or os.path.getsize(downloaded_image) == 0:
                    logger.error(f"Skipping scene {scene['scene_number']}: image file is missing or empty")
                    continue
                
                logger.info(f"Successfully downloaded image for scene {scene['scene_number']}: {downloaded_image} ({os.path.getsize(downloaded_image)} bytes)")
                
                # Video dimensions (9:16 aspect ratio)
                video_width = 1080
                video_height = 1920
                
                try:
                    # Create image clip and resize to fill the entire frame
                    temp_clip = ImageClip(downloaded_image)
                    
                    # Validate image dimensions
                    if temp_clip.w == 0 or temp_clip.h == 0:
                        logger.error(f"Skipping scene {scene['scene_number']}: image has invalid dimensions ({temp_clip.w}x{temp_clip.h})")
                        continue
                    
                    logger.info(f"Scene {scene['scene_number']} image dimensions: {temp_clip.w}x{temp_clip.h}")
                    
                    # Calculate scaling to fill frame (crop excess)
                    clip_aspect = temp_clip.w / temp_clip.h
                    video_aspect = video_width / video_height
                    
                    if clip_aspect > video_aspect:
                        # Image is wider - scale by height and crop width
                        new_width = int(temp_clip.w * (video_height / temp_clip.h))
                        logger.info(f"Scene {scene['scene_number']}: Scaling by height. New dimensions before crop: {new_width}x{video_height}")
                        image_clip = (temp_clip
                                     .resize(height=video_height)
                                     .crop(x_center=new_width/2, width=video_width, height=video_height)
                                     .set_duration(audio_clip.duration))
                    else:
                        # Image is taller - scale by width and crop height  
                        new_height = int(temp_clip.h * (video_width / temp_clip.w))
                        logger.info(f"Scene {scene['scene_number']}: Scaling by width. New dimensions before crop: {video_width}x{new_height}")
                        image_clip = (temp_clip
                                     .resize(width=video_width)
                                     .crop(y_center=new_height/2, width=video_width, height=video_height)
                                     .set_duration(audio_clip.duration))
                    
                    # Combine image, text, and audio
                    video_clip = image_clip.set_audio(audio_clip)

                    # Apply transition effect
                    transition_type = scene['transition_type']
                    
                    logger.info(f"Adding clip for scene {scene['scene_number']} with transition: {transition_type}")
                        
                    if transition_type == 'zoom-in':
                        clips.append(zoom(video_clip))
                    elif transition_type == 'zoom-out':
                        clips.append(zoom(video_clip, mode='out'))
                    else:
                        clips.append(video_clip)
                        
                except Exception as e:
                    logger.error(f"Error processing image for scene {scene['scene_number']}: {str(e)}")
                    continue

            timings['clip_creation'] = time.time() - start_clips
            
            if not clips:
                logger.error("No valid clips generated")
                return None
            
            logger.info(f"Total clips generated: {len(clips)}")
            logger.info(f"Timing - Audio generation: {timings['audio_generation']:.2f}s, Clip creation: {timings['clip_creation']:.2f}s")

            # Add closing screen
            start_closing = time.time()
            if progress_callback:
                await progress_callback(0.915, "Creating closing screen...")
            closing_screen = self.create_closing_screen(duration=4)
            if closing_screen:
                clips.append(closing_screen)
                logger.info("Added closing screen with logos to video")
            timings['closing_screen'] = time.time() - start_closing
            
            # Add audio fadeout to last scene clip to prevent audio artifacts
            if len(clips) > 1 and clips[-2].audio is not None:
                clips[-2] = clips[-2].audio_fadeout(0.3)
            
            if progress_callback:
                await progress_callback(0.918, "Combining clips...")
            
            start_concat = time.time()
            final_clip = concatenate_videoclips(clips, method="compose")
            timings['concatenation'] = time.time() - start_concat
            
            # Use a separate thread for video writing to avoid blocking the event loop
            # Optimized settings: faster preset, lower fps for speed
            start_encoding = time.time()
            if progress_callback:
                await progress_callback(0.92, "Encoding video...")
            
            await asyncio.to_thread(
                final_clip.write_videofile,
                video_path,
                fps=20,  # Reduced from 24 for faster encoding
                codec='libx264',
                audio_codec='aac',
                audio_bitrate='192k',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                preset='faster',  # Changed from 'medium' for ~2x speed boost
                threads=4,
                logger=None  # Suppress MoviePy's verbose output
            )
            timings['video_encoding'] = time.time() - start_encoding
            logger.info(f"Video encoding completed in {timings['video_encoding']:.2f}s")

            start_captions = time.time()
            if progress_callback:
                await progress_callback(0.96, "Adding captions...")
            
            subtitle_video_path = video_path.replace('.mp4', '_subtitle.mp4')
            await self.add_captions(video_path, subtitle_video_path, caption_font, custom_segments=subtitle_segments)
            timings['caption_generation'] = time.time() - start_captions
            
            timings['total'] = time.time() - start_total
            
            # Log detailed timing breakdown
            logger.info(f"=== Video Generation Timing Breakdown ===")
            logger.info(f"Audio generation: {timings.get('audio_generation', 0):.2f}s")
            logger.info(f"Clip creation: {timings.get('clip_creation', 0):.2f}s")
            logger.info(f"Closing screen: {timings.get('closing_screen', 0):.2f}s")
            logger.info(f"Concatenation: {timings.get('concatenation', 0):.2f}s")
            logger.info(f"Video encoding: {timings.get('video_encoding', 0):.2f}s")
            logger.info(f"Caption generation: {timings.get('caption_generation', 0):.2f}s")
            logger.info(f"TOTAL TIME: {timings['total']:.2f}s")
            logger.info(f"========================================")

            return subtitle_video_path
        except Exception as e:
            logger.error(f"Error in generate_video: {str(e)}")
            return None
