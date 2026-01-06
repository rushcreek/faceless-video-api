import os
import asyncio
import time

# Configure ImageMagick for MoviePy before importing
import moviepy.config as moviepy_config
IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
if os.path.exists(IMAGEMAGICK_BINARY):
    moviepy_config.change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

from moviepy.editor import (
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeVideoClip,
    ColorClip,
    AudioClip,
    TextClip,
    VideoFileClip
)
from app.services.audio_generator import AudioGenerator
from app.services.image_api import runware_flux_api, runware_pocketrag_image_api
from app.utils.transitions import zoom 
from app.core.config import settings
from app.core.logging import logger
from app.utils.image_utils import download_image
from app.models.image import Image
from PIL import Image as PILImage
import json
import openai
from difflib import SequenceMatcher

class VideoGenerator:
    def __init__(self, client=None):
        # client parameter kept for backward compatibility but not used with Cartesia
        self.audio_generator = AudioGenerator()
        self.font_path = os.path.join(settings.BASE_DIR, "resources/fonts")
        self.assets_path = os.path.join(os.path.dirname(settings.BASE_DIR), "assets")
    
    def has_pocketrag_mention(self, text: str) -> bool:
        """Check if text mentions PocketRAG in any form"""
        text_lower = text.lower()
        pocketrag_variations = ['pocketrag', 'pocket rag', 'pocket-rag']
        return any(variation in text_lower for variation in pocketrag_variations)
    
    def align_script_with_transcription(self, original_text, transcription_words, audio_duration=None):
        """
        Align original script words (with punctuation) to Whisper transcription words (with timing).
        Returns words from original script with timing from transcription.
        
        If audio_duration is provided, ensures words span the full audio duration.
        """
        # Clean words for matching (remove punctuation, lowercase)
        import re
        
        def clean_word(word):
            return re.sub(r'[^\w\s]', '', word.lower()).strip()
        
        # Split original text into words, preserving original form
        original_words = original_text.split()
        
        if not original_words:
            return []
        
        # If no transcription or audio_duration provided, use even distribution as fallback
        if not transcription_words:
            if audio_duration:
                word_duration = audio_duration / len(original_words)
                return [{
                    "word": " " + word,
                    "start": i * word_duration,
                    "end": (i + 1) * word_duration
                } for i, word in enumerate(original_words)]
            else:
                return [{
                    "word": " " + word,
                    "start": i * 0.3,
                    "end": (i + 1) * 0.3
                } for i, word in enumerate(original_words)]
        
        # Extract clean transcription words
        transcribed_clean = [clean_word(w['word']) for w in transcription_words]
        original_clean = [clean_word(w) for w in original_words]
        
        # Get the full audio span from transcription
        trans_start = transcription_words[0]['start']
        trans_end = transcription_words[-1]['end']
        
        # If audio_duration is provided and longer than transcription, use it
        if audio_duration and audio_duration > trans_end:
            actual_end = audio_duration
        else:
            actual_end = trans_end
        
        # Use sequence matcher to align
        matcher = SequenceMatcher(None, original_clean, transcribed_clean)
        aligned_words = []
        
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
                    # Different lengths - distribute timing evenly across the trans_chunk span
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
        
        # CRITICAL FIX: Ensure the last word extends to fill the audio duration
        # This keeps captions visible for the entire scene even if speech ends early
        if aligned_words and audio_duration:
            last_word_end = aligned_words[-1]['end']
            if last_word_end < audio_duration:
                # Extend the last word's display time to fill the audio
                logger.debug(f"Extending last word from {last_word_end:.2f}s to {audio_duration:.2f}s")
                aligned_words[-1]['end'] = audio_duration
        
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
                    model="whisper-1",  # Use standard Whisper model - supports verbose_json
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
            prlogo_img = PILImage.open(prlogo_path)
            appstore_img = PILImage.open(appstore_path)
            
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

    async def add_captions(self, output_file, output_file_subtitle, caption_font='BebasNeue', custom_segments=None, progress_callback=None):
        """Add phrase-based captions to video using MoviePy directly"""
        try:
            if progress_callback:
                await progress_callback(0.90, "Adding captions: Loading video...")
            
            logger.info(f"🎬 Starting caption generation with MoviePy")
            logger.info(f"  Input video: {output_file}")
            logger.info(f"  Output video: {output_file_subtitle}")
            logger.info(f"  Font: {caption_font}")
            logger.info(f"  Segments provided: {len(custom_segments) if custom_segments else 0}")
            
            font_path = os.path.join(self.font_path, f"{caption_font}.ttf")
            
            if not custom_segments:
                raise ValueError("Custom segments required for caption generation")
            
            # Run caption generation in a thread to avoid blocking
            await asyncio.to_thread(
                self._add_captions_moviepy_sync,
                output_file,
                output_file_subtitle,
                font_path,
                custom_segments,
                progress_callback
            )
            
            logger.info(f"✅ Caption generation completed successfully")
            logger.info(f"  Output file created: {os.path.exists(output_file_subtitle)}")
            if os.path.exists(output_file_subtitle):
                file_size = os.path.getsize(output_file_subtitle) / (1024 * 1024)
                logger.info(f"  Output file size: {file_size:.2f} MB")
            
        except Exception as e:
            logger.error(f"❌ Error in add_captions: {type(e).__name__}: {str(e)}")
            logger.error(f"  Stack trace:", exc_info=True)
            raise
    
    def _add_captions_moviepy_sync(self, video_file, output_file, font_path, segments, progress_callback=None):
        """
        Phrase-based captions with word-by-word yellow highlighting.
        - Shows multiple words at a time (phrase)
        - White text for all words in phrase
        - Yellow highlight on currently spoken word
        - Strong shadow for readability on light backgrounds
        """
        from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
        import os
        import asyncio
        
        # Helper to call async progress_callback from sync context
        def update_progress(progress, message):
            if progress_callback:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(progress_callback(progress, message), loop)
                except:
                    pass  # Ignore errors in progress updates
        
        logger.info("Loading video file for captions...")
        update_progress(0.91, "Adding captions: Loading video...")
        video = VideoFileClip(video_file)
        
        # Validate font exists - log detailed info
        logger.info(f"🔤 Font path received: {font_path}")
        if os.path.exists(font_path):
            logger.info(f"✅ Font file exists: {font_path}")
        else:
            logger.error(f"❌ Font file NOT found: {font_path}")
            # Try to find available fonts
            font_dir = os.path.dirname(font_path)
            if os.path.exists(font_dir):
                available_fonts = [f for f in os.listdir(font_dir) if f.endswith('.ttf')]
                logger.info(f"Available fonts in {font_dir}: {available_fonts}")
                if available_fonts:
                    font_path = os.path.join(font_dir, available_fonts[0])
                    logger.info(f"Using fallback font: {font_path}")
        
        # Collect all words with timing from segments
        all_words = []
        for segment in segments:
            words = segment.get('words', [])
            for word_data in words:
                word_text = word_data.get('word', '').strip()
                if word_text:
                    all_words.append({
                        'text': word_text,
                        'start': word_data.get('start', 0),
                        'end': word_data.get('end', 0)
                    })
        
        logger.info(f"Processing {len(all_words)} words for captions")
        
        if not all_words:
            logger.warning("No words found in segments")
            video.write_videofile(output_file, codec='libx264', audio_codec='aac')
            video.close()
            return
        
        # Caption settings
        FONT_SIZE = 80
        MAX_WORDS_PER_PHRASE = 5  # Show up to 5 words at a time
        WORD_SPACING = 18  # Space between words
        
        # Position captions in lower third (more common for video captions)
        caption_y = int(video.h * 0.75)
        
        logger.info(f"Caption settings: font_size={FONT_SIZE}, y={caption_y}, max_words={MAX_WORDS_PER_PHRASE}")
        update_progress(0.92, "Adding captions: Measuring words...")
        
        # Pre-measure word widths
        word_widths = {}
        for word in all_words:
            if word['text'] not in word_widths:
                try:
                    test_clip = TextClip(word['text'], fontsize=FONT_SIZE, font=font_path, color='white')
                    word_widths[word['text']] = test_clip.w
                    test_clip.close()
                except:
                    word_widths[word['text']] = FONT_SIZE * len(word['text']) * 0.6
        
        # Group words into phrases
        def ends_sentence(text):
            return text.rstrip().endswith(('.', '!', '?'))
        
        phrases = []
        i = 0
        while i < len(all_words):
            phrase_words = []
            phrase_width = 0
            max_width = video.w * 0.85
            
            while i < len(all_words) and len(phrase_words) < MAX_WORDS_PER_PHRASE:
                word = all_words[i]
                word_w = word_widths.get(word['text'], 50)
                new_width = phrase_width + word_w + (WORD_SPACING if phrase_words else 0)
                
                if new_width > max_width and phrase_words:
                    break
                    
                phrase_words.append(word)
                phrase_width = new_width
                i += 1
                
                # Break at sentence boundaries
                if ends_sentence(word['text']):
                    break
            
            if phrase_words:
                phrases.append({
                    'words': phrase_words,
                    'start': phrase_words[0]['start'],
                    'end': phrase_words[-1]['end'],
                    'width': phrase_width
                })
        
        logger.info(f"Created {len(phrases)} phrases from {len(all_words)} words")
        update_progress(0.93, "Adding captions: Rendering phrases...")
        
        caption_clips = []
        
        for phrase_idx, phrase in enumerate(phrases):
            if phrase_idx % 5 == 0:
                logger.info(f"  Processing phrase {phrase_idx + 1}/{len(phrases)}")
            
            phrase_start = phrase['start']
            phrase_end = phrase['end']
            phrase_duration = phrase_end - phrase_start
            
            if phrase_duration <= 0:
                continue
            
            # Calculate starting x position to center the phrase
            phrase_width = phrase['width']
            start_x = (video.w - phrase_width) // 2
            
            # Build word positions
            word_positions = []
            x = start_x
            for word in phrase['words']:
                word_positions.append(x)
                x += word_widths.get(word['text'], 50) + WORD_SPACING
            
            # Create clips for each word in the phrase
            for word_idx, word in enumerate(phrase['words']):
                word_x = word_positions[word_idx]
                word_text = word['text']
                
                try:
                    # === SHADOW LAYERS (multiple for stronger effect) ===
                    # Shadow 1: Bottom-right offset
                    shadow1 = TextClip(word_text, fontsize=FONT_SIZE, font=font_path, color='black')
                    shadow1 = shadow1.set_position((word_x + 4, caption_y + 4))
                    shadow1 = shadow1.set_start(phrase_start).set_duration(phrase_duration)
                    caption_clips.append(shadow1)
                    
                    # Shadow 2: Slight offset for thickness
                    shadow2 = TextClip(word_text, fontsize=FONT_SIZE, font=font_path, color='black')
                    shadow2 = shadow2.set_position((word_x + 2, caption_y + 2))
                    shadow2 = shadow2.set_start(phrase_start).set_duration(phrase_duration)
                    caption_clips.append(shadow2)
                    
                    # Shadow 3: Left offset for balanced shadow
                    shadow3 = TextClip(word_text, fontsize=FONT_SIZE, font=font_path, color='black')
                    shadow3 = shadow3.set_position((word_x - 2, caption_y + 2))
                    shadow3 = shadow3.set_start(phrase_start).set_duration(phrase_duration)
                    caption_clips.append(shadow3)
                    
                    # === WHITE BASE TEXT (visible for entire phrase duration) ===
                    white_clip = TextClip(word_text, fontsize=FONT_SIZE, font=font_path, color='white')
                    white_clip = white_clip.set_position((word_x, caption_y))
                    white_clip = white_clip.set_start(phrase_start).set_duration(phrase_duration)
                    caption_clips.append(white_clip)
                    
                    # === YELLOW HIGHLIGHT (only when this word is being spoken) ===
                    word_start = word['start']
                    word_end = word['end']
                    highlight_duration = word_end - word_start
                    
                    if highlight_duration > 0:
                        yellow_clip = TextClip(word_text, fontsize=FONT_SIZE, font=font_path, color='yellow')
                        yellow_clip = yellow_clip.set_position((word_x, caption_y))
                        yellow_clip = yellow_clip.set_start(word_start).set_duration(highlight_duration)
                        caption_clips.append(yellow_clip)
                    
                except Exception as e:
                    logger.error(f"Error creating clip for word '{word_text}': {e}")
                    continue
        
        logger.info(f"Created {len(caption_clips)} caption elements")
        logger.info("Compositing video with captions...")
        update_progress(0.95, "Adding captions: Compositing layers...")
        
        final_video = CompositeVideoClip([video] + caption_clips)
        
        logger.info("Encoding final video...")
        update_progress(0.96, "Adding captions: Encoding final video...")
        final_video.write_videofile(
            output_file,
            codec='libx264',
            audio_codec='aac',
            fps=video.fps,
            preset='faster',
            threads=4,
            logger=None
        )
        
        # Cleanup
        logger.info("Cleaning up resources...")
        for clip in caption_clips:
            try:
                clip.close()
            except:
                pass
        
        video.close()
        final_video.close()
        
        logger.info("✅ Caption generation complete!")
    
    def _add_captions_sync(self, video_file, output_file, font_path, segments):
        """DEPRECATED - keeping for compatibility but not used"""
        import shortcap
        
        logger.info(f"📝 Adding captions using shortcap...")
        
        try:
            # Use shortcap with the exact settings from working commit bb7a634
            shortcap.add_captions(
                video_file=video_file,
                output_file=output_file,
                font=font_path,
                font_size=80,
                font_color="white",
                stroke_width=3,
                stroke_color="black",
                shadow_strength=1.0,
                shadow_blur=0.1,
                highlight_current_word=True,
                word_highlight_color="yellow",
                line_count=2,
                use_local_whisper=False,
            )
            
            logger.info("✅ Shortcap caption generation complete!")
            
        except Exception as e:
            logger.error(f"Error adding captions with shortcap: {e}")
            raise

    async def generate_video(self, storyboard_project, story_dir, voice_name, caption_font='BebasNeue', progress_callback=None, task_id=None):
        audio_dir = os.path.join(story_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        video_path = os.path.join(story_dir, "story_video.mp4")
        clips = []
        
        # NOTE: Image validation moved to after image generation (images are generated in this function now)
        
        # Timing profiling
        timings = {}
        start_total = time.time()
        
        # Store subtitle timing info for custom caption segments
        # NOTE: We'll build this AFTER clip creation to ensure sync with actual video
        subtitle_segments = []
        current_time = 0.0  # Used during audio/image generation phase
        clip_current_time = 0.0  # Used during clip creation phase for accurate caption timing
        
        try:
            # Audio generation, transcription, and caption phrase/timing
            start_audio = time.time()
            for scene in storyboard_project['storyboards']:
                audio_file = os.path.join(audio_dir, f"scene_{scene['scene_number']}.mp3")
                
                # Check if cached audio matches current subtitle text
                # Use a hash file to track what text was used to generate the audio
                import hashlib
                subtitle_hash = hashlib.md5(scene['subtitles'].encode()).hexdigest()[:8]
                hash_file = audio_file.replace('.mp3', '.hash')
                
                audio_needs_regeneration = True
                if os.path.exists(audio_file) and os.path.exists(hash_file):
                    try:
                        with open(hash_file, 'r') as f:
                            cached_hash = f.read().strip()
                        if cached_hash == subtitle_hash:
                            logger.info(f"♻️ Audio file already exists for scene {scene['scene_number']} with matching content, skipping generation")
                            audio_needs_regeneration = False
                        else:
                            logger.info(f"⚠️ Audio file exists for scene {scene['scene_number']} but content changed (hash mismatch), regenerating")
                    except Exception as e:
                        logger.warning(f"Could not read hash file for scene {scene['scene_number']}: {e}")
                elif os.path.exists(audio_file):
                    logger.info(f"⚠️ Audio file exists for scene {scene['scene_number']} but no hash file found, regenerating to ensure sync")
                
                if audio_needs_regeneration:
                    success = await self.audio_generator.generate_audio(scene['subtitles'], audio_file, voice_name)
                    if not success:
                        logger.error(f"Failed to generate audio for scene {scene['scene_number']}")
                        continue
                    # Save the hash for future runs
                    try:
                        with open(hash_file, 'w') as f:
                            f.write(subtitle_hash)
                    except Exception as e:
                        logger.warning(f"Could not write hash file for scene {scene['scene_number']}: {e}")
                audio_clip = AudioFileClip(audio_file)
                duration = audio_clip.duration
                scene['audio_duration'] = duration
                logger.info(f"Scene {scene['scene_number']} audio duration: {duration:.2f}s")
                if task_id and scene.get('audio_duration') != duration:
                    await Image.update_by_task_and_scene(
                        task_id=task_id,
                        scene_number=scene['scene_number'],
                        audio_duration=duration
                    )
                    logger.info(f"✅ Updated database: scene {scene['scene_number']} audio_duration={duration:.2f}s")
                logger.info(f"Transcribing scene {scene['scene_number']} for accurate timing...")
                transcription_words = await self.transcribe_audio_with_whisper(audio_file)
                
                # Log what Whisper transcribed vs original script for debugging sync issues
                if transcription_words:
                    whisper_text = " ".join([w['word'].strip() for w in transcription_words])
                    logger.info(f"Scene {scene['scene_number']} TRANSCRIPTION DEBUG:")
                    logger.info(f"  Original script: '{scene['subtitles']}'")
                    logger.info(f"  Whisper heard:   '{whisper_text}'")
                    logger.info(f"  Original words: {len(scene['subtitles'].split())}, Whisper words: {len(transcription_words)}")
                    
                    # Check if transcription is wildly different from script (audio mismatch)
                    # Normalize both strings for comparison
                    import re
                    def normalize_text(text):
                        return re.sub(r'[^\w\s]', '', text.lower()).split()
                    
                    orig_words = normalize_text(scene['subtitles'])
                    whisper_words = normalize_text(whisper_text)
                    
                    # Check if first and last words roughly match (allowing for minor variations)
                    if orig_words and whisper_words:
                        first_match = orig_words[0][:3] == whisper_words[0][:3] if len(orig_words[0]) >= 3 and len(whisper_words[0]) >= 3 else orig_words[0] == whisper_words[0]
                        last_match = orig_words[-1][:3] == whisper_words[-1][:3] if len(orig_words[-1]) >= 3 and len(whisper_words[-1]) >= 3 else orig_words[-1] == whisper_words[-1]
                        
                        if not first_match and not last_match:
                            logger.error(f"⚠️ AUDIO MISMATCH DETECTED for scene {scene['scene_number']}!")
                            logger.error(f"   Audio file may contain wrong content. Captions may be incorrect.")
                
                # Store RELATIVE word timing (relative to scene start, not absolute)
                # We'll convert to absolute timing during clip creation
                relative_word_segments = []
                if transcription_words:
                    logger.info(f"Aligning script with transcription for scene {scene['scene_number']}...")
                    aligned_words = self.align_script_with_transcription(
                        scene['subtitles'], 
                        transcription_words,
                        audio_duration=duration  # Pass audio duration to ensure words fill the scene
                    )
                    for word in aligned_words:
                        relative_word_segments.append({
                            "word": word["word"],
                            "start": word["start"],  # Relative to scene start
                            "end": word["end"]       # Relative to scene start
                        })
                else:
                    logger.warning(f"Transcription failed for scene {scene['scene_number']}, using fallback timing")
                    words = scene['subtitles'].split()
                    if words:
                        word_duration = duration / len(words)
                        for i, word in enumerate(words):
                            word_start = i * word_duration
                            word_end = word_start + word_duration
                            relative_word_segments.append({
                                "word": " " + word,
                                "start": word_start,  # Relative to scene start
                                "end": word_end       # Relative to scene start
                            })
                
                # Store in scene object for use during clip creation
                scene['_word_segments'] = relative_word_segments
                
                # --- IMAGE PROMPT GENERATION AND IMAGE GENERATION ---
                # Use the actual words for this scene (as a single string) for the prompt
                caption_phrase = " ".join([w['word'].strip() for w in relative_word_segments])
                fallback_used = False
                # Fallback if caption_phrase is empty or too short
                if not caption_phrase.strip() or len(caption_phrase.strip()) < 3:
                    fallback_used = True
                    # Prefer description, then subtitles
                    fallback_prompt = scene.get('description', '') or scene.get('subtitles', '')
                    prompt = f"{fallback_prompt} | {storyboard_project.get('characters', [])}"
                    logger.warning(f"Scene {scene['scene_number']}: Caption phrase too short/empty, using fallback prompt: {prompt}")
                else:
                    prompt = f"{caption_phrase} | {storyboard_project.get('characters', [])} | {scene.get('description', '')}"
                logger.info(f"Scene {scene['scene_number']}: Image prompt: {prompt}")
                
                # Check if THIS SPECIFIC SCENE mentions PocketRAG - use reference images and special prompt if so
                # NOTE: Only check scene-specific content (description, subtitles), NOT project title
                # to avoid triggering PocketRAG mode for ALL scenes when only some mention it
                description = scene.get('description', '')
                subtitles = scene.get('subtitles', '')
                is_pocketrag = (self.has_pocketrag_mention(description) or 
                               self.has_pocketrag_mention(subtitles))
                
                if is_pocketrag:
                    # REPLACE the prompt with PocketRAG-specific iPhone instruction
                    pocketrag_instruction = "A person holding a modern iPhone (black or white), with the iPhone screen displayed and visible. The iPhone screen shows the PocketRAG mobile app. Professional office setting with soft natural lighting from windows in the background. The phone is the main focus, screen content clearly readable."
                    prompt = f"{pocketrag_instruction} | {caption_phrase}"
                    logger.info(f"🎯 Scene {scene['scene_number']}: POCKETRAG DETECTED - REPLACED prompt with iPhone instruction")
                    logger.info(f"🎯 New prompt: {prompt[:150]}...")
                    
                    # Use PocketRAG reference images - cycle through them
                    pocketrag_reference_images = [
                        "https://pub-2b7fb33554fe43f38a78452469fe75c0.r2.dev/IMG_4317.PNG",
                        "https://pub-2b7fb33554fe43f38a78452469fe75c0.r2.dev/Screenshot%202025-12-31%20at%201.47.33%E2%80%AFPM.png",
                        "https://pub-2b7fb33554fe43f38a78452469fe75c0.r2.dev/Screenshot%202025-12-31%20at%201.49.28%E2%80%AFPM.png",
                        "https://pub-2b7fb33554fe43f38a78452469fe75c0.r2.dev/Screenshot%202025-12-31%20at%201.50.21%E2%80%AFPM.png"
                    ]
                    reference_image_url = pocketrag_reference_images[scene['scene_number'] % len(pocketrag_reference_images)]
                    logger.info(f"🎯 Using reference image: {reference_image_url}")
                    result = await runware_pocketrag_image_api(task_id, prompt, reference_image_url)
                else:
                    # Regular image generation
                    result = await runware_flux_api(task_id, prompt)
                
                # Process result - both APIs return {"url": image_url, "cost": cost} or None
                if result and isinstance(result, dict):
                    image_url = result.get('url')
                    scene['image'] = image_url
                    scene['image_generation_cost'] = result.get('cost')
                    logger.info(f"Generated image for scene {scene['scene_number']}: {image_url} (cost: {result.get('cost')})")
                else:
                    scene['image'] = None
                    logger.error(f"Image generation FAILED for scene {scene['scene_number']} with prompt: {prompt}")
                current_time += duration
                audio_clip.close()
            timings['audio_generation'] = time.time() - start_audio
            
            # CRITICAL: Validate all scenes have valid images AFTER image generation
            logger.info("🔍 Validating images after generation...")
            missing_or_failed = []
            for scene in storyboard_project['storyboards']:
                image_url = scene.get('image')
                scene_number = scene.get('scene_number', 'unknown')
                
                if not image_url:
                    missing_or_failed.append(f"Scene {scene_number}")
            
            if missing_or_failed:
                error_msg = f"Image generation failed for {len(missing_or_failed)} scene(s): {', '.join(missing_or_failed)}. Cannot proceed with video generation."
                logger.error(f"❌ FATAL: {error_msg}")
                raise ValueError(error_msg)
            
            logger.info("✅ All scenes have valid image URLs")
            
            # Save images to database now that they've been generated
            if task_id:
                from uuid import uuid4
                from app.models.image import Image
                logger.info(f"💾 Saving {len(storyboard_project['storyboards'])} image records to database...")
                for scene in storyboard_project['storyboards']:
                    image_url = scene.get('image')
                    scene_number = scene.get('scene_number')
                    image_data = {
                        "id": str(uuid4()),
                        "task_id": task_id,
                        "scene_number": scene_number,
                        "urls": [image_url] if image_url else [],
                        "subtitles": scene.get('subtitles', ''),
                        "status": "completed" if image_url else "failed",
                        "enhanced_prompt": scene.get('enhanced_prompt', ''),
                        "video_generation_request": scene.get('video_generation_request'),
                        "audio_duration": scene.get('audio_duration'),
                        "image_generation_cost": scene.get('image_generation_cost'),
                        "error_message": scene.get('error_message', '')
                    }
                    await Image.create(**image_data)
                    logger.info(f"  ✅ Saved scene {scene_number} to database")
                logger.info(f"✅ All image records saved to database")
            
            if progress_callback:
                await progress_callback(0.52, "Processing clips...")
            # Image processing and clip creation phase
            start_clips = time.time()
            for scene in storyboard_project['storyboards']:
                audio_file = os.path.join(audio_dir, f"scene_{scene['scene_number']}.mp3")
                if not os.path.exists(audio_file):
                    continue
                audio_clip = AudioFileClip(audio_file)
                
                # Check if this scene mentions PocketRAG - if so, force static image
                description = scene.get('description', '')
                subtitles = scene.get('subtitles', '')
                is_pocketrag_scene = self.has_pocketrag_mention(description) or self.has_pocketrag_mention(subtitles)
                
                if is_pocketrag_scene:
                    logger.info(f"🎯 Scene {scene['scene_number']} DETECTED as PocketRAG scene")
                    logger.info(f"  Description: '{description[:100]}...'")
                    logger.info(f"  Subtitles: '{subtitles[:100]}...'")
                    logger.info(f"  Image URL: {scene.get('image', 'NONE')}")
                    logger.info(f"  Video Clip URL: {scene.get('video_clip_url', 'NONE')}")
                
                # Check if this scene has a video clip (animated) or just static image
                # Override video_clip_url for PocketRAG scenes to force static image usage
                video_clip_url = scene.get('video_clip_url')
                if is_pocketrag_scene and video_clip_url:
                    logger.info(f"🎯 Scene {scene['scene_number']} is PocketRAG - OVERRIDING video clip, using static image instead")
                    video_clip_url = None
                
                logger.debug(f"Scene {scene['scene_number']} video_clip_url: {video_clip_url}, is_pocketrag: {is_pocketrag_scene}")
                
                if video_clip_url:
                    # Use animated video clip
                    logger.info(f"🎬 Using video clip for scene {scene['scene_number']}: {video_clip_url}")
                    video_ext = '.mp4'
                    scene_video_path = os.path.join(story_dir, f"scene_{scene['scene_number']}{video_ext}")
                    downloaded_video = await download_image(video_clip_url, scene_video_path)  # Reuse download function
                    
                    if downloaded_video is None or not os.path.exists(downloaded_video):
                        logger.error(f"Failed to download video clip for scene {scene['scene_number']}, falling back to static image")
                        video_clip_url = None  # Fall back to static image
                    else:
                        logger.info(f"Successfully downloaded video clip for scene {scene['scene_number']}: {downloaded_video}")
                
                if not video_clip_url:
                    # Download and use the static image
                    image_url = scene.get('image')
                    
                    if not image_url:
                        logger.error(f"Skipping scene {scene['scene_number']}: no image URL available")
                        audio_clip.close()  # Clean up before skipping
                        continue
                    
                    image_ext = '.jpg' if image_url.endswith('.jpg') else '.png'
                    image_path = os.path.join(story_dir, f"scene_{scene['scene_number']}{image_ext}")
                    downloaded_image = await download_image(image_url, image_path)
                
                    if downloaded_image is None:
                        logger.error(f"Skipping scene {scene['scene_number']} due to image download failure")
                        audio_clip.close()  # Clean up before skipping
                        continue
                
                    # Validate the downloaded image file exists and has content
                    if not os.path.exists(downloaded_image) or os.path.getsize(downloaded_image) == 0:
                        logger.error(f"Skipping scene {scene['scene_number']}: image file is missing or empty")
                        audio_clip.close()  # Clean up before skipping
                        continue
                
                    logger.info(f"Successfully downloaded image for scene {scene['scene_number']}: {downloaded_image} ({os.path.getsize(downloaded_image)} bytes)")
                
                # Video dimensions (9:16 aspect ratio)
                video_width = 1080
                video_height = 1920
                
                try:
                    if video_clip_url and os.path.exists(downloaded_video):
                        # Use video clip - import VideoFileClip
                        from moviepy.editor import VideoFileClip
                        
                        # Load the video clip
                        temp_clip = VideoFileClip(downloaded_video)
                        video_duration = temp_clip.duration
                        audio_duration = audio_clip.duration
                        logger.info(f"Scene {scene['scene_number']} video clip - original: {temp_clip.w}x{temp_clip.h}, video duration: {video_duration:.2f}s, audio duration: {audio_duration:.2f}s")
                        
                        # Calculate scaling to fill frame (crop excess)
                        clip_aspect = temp_clip.w / temp_clip.h
                        video_aspect = video_width / video_height
                        
                        if clip_aspect > video_aspect:
                            # Video is wider - scale by height and crop width
                            new_width = int(temp_clip.w * (video_height / temp_clip.h))
                            logger.info(f"Scene {scene['scene_number']}: Scaling by height. New dimensions before crop: {new_width}x{video_height}")
                            scaled_clip = (temp_clip
                                         .resize(height=video_height)
                                         .crop(x_center=new_width/2, width=video_width, height=video_height))
                        else:
                            # Video is taller - scale by width and crop height  
                            new_height = int(temp_clip.h * (video_width / temp_clip.w))
                            logger.info(f"Scene {scene['scene_number']}: Scaling by width. New dimensions before crop: {video_width}x{new_height}")
                            scaled_clip = (temp_clip
                                         .resize(width=video_width)
                                         .crop(y_center=new_height/2, width=video_width, height=video_height))
                        
                        # Handle duration mismatch between video and audio
                        if abs(video_duration - audio_duration) > 0.5:
                            # Significant difference - need to adjust
                            if video_duration < audio_duration:
                                # Video is shorter - loop it to match audio duration
                                logger.info(f"Scene {scene['scene_number']}: Video shorter than audio, looping to match ({video_duration:.2f}s -> {audio_duration:.2f}s)")
                                loops_needed = int(audio_duration / video_duration) + 1
                                video_clip = concatenate_videoclips([scaled_clip] * loops_needed).set_duration(audio_duration)
                            else:
                                # Video is longer - trim to audio duration
                                logger.info(f"Scene {scene['scene_number']}: Video longer than audio, trimming ({video_duration:.2f}s -> {audio_duration:.2f}s)")
                                video_clip = scaled_clip.set_duration(audio_duration)
                        else:
                            # Close enough - just set duration to match exactly
                            video_clip = scaled_clip.set_duration(audio_duration)
                        
                        # Replace audio with generated speech
                        video_clip = video_clip.set_audio(audio_clip)
                        logger.info(f"Scene {scene['scene_number']}: Final clip duration set to {audio_duration:.2f}s")
                        
                    else:
                        # Use static image with zoom effect
                        # Create image clip and resize to fill the entire frame
                        temp_clip = ImageClip(downloaded_image)
                    
                        # Validate image dimensions
                        if temp_clip.w == 0 or temp_clip.h == 0:
                            logger.error(f"Skipping scene {scene['scene_number']}: image has invalid dimensions ({temp_clip.w}x{temp_clip.h})")
                            audio_clip.close()  # Clean up before skipping
                            continue
                        
                        audio_duration = audio_clip.duration
                        logger.info(f"Scene {scene['scene_number']} static image - dimensions: {temp_clip.w}x{temp_clip.h}, audio duration: {audio_duration:.2f}s")
                        
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
                                         .set_duration(audio_duration))
                        else:
                            # Image is taller - scale by width and crop height  
                            new_height = int(temp_clip.h * (video_width / temp_clip.w))
                            logger.info(f"Scene {scene['scene_number']}: Scaling by width. New dimensions before crop: {video_width}x{new_height}")
                            image_clip = (temp_clip
                                         .resize(width=video_width)
                                         .crop(y_center=new_height/2, width=video_width, height=video_height)
                                         .set_duration(audio_duration))
                        
                        # Combine image and audio
                        video_clip = image_clip.set_audio(audio_clip)
                        logger.info(f"Scene {scene['scene_number']}: Final clip duration set to {audio_duration:.2f}s")
                    
                    # Add audio fade in/out to prevent artifacts between clips
                    video_clip = video_clip.audio_fadein(0.1).audio_fadeout(0.1)

                    # Apply transition effect (only for static images, not video clips)
                    transition_type = scene.get('transition_type', 'zoom-in')  # Default to zoom-in for static images
                    
                    logger.info(f"Adding clip for scene {scene['scene_number']} (type: {'video' if video_clip_url else 'image'}) with transition: {transition_type}")
                        
                    # Only apply zoom transitions to static images
                    if not video_clip_url and transition_type == 'zoom-in':
                        clips.append(zoom(video_clip))
                    elif not video_clip_url and transition_type == 'zoom-out':
                        clips.append(zoom(video_clip, mode='out'))
                    else:
                        clips.append(video_clip)
                    
                    # Build subtitle_segments with CORRECT timing (only for clips that make it into the video)
                    relative_words = scene.get('_word_segments', [])
                    if relative_words:
                        # Convert relative timing to absolute timing based on clip_current_time
                        absolute_word_segments = []
                        for word in relative_words:
                            absolute_word_segments.append({
                                "word": word["word"],
                                "start": clip_current_time + word["start"],
                                "end": clip_current_time + word["end"]
                            })
                        subtitle_segments.append({
                            "start": clip_current_time,
                            "end": clip_current_time + audio_duration,
                            "words": absolute_word_segments
                        })
                        logger.info(f"Scene {scene['scene_number']}: Added subtitle segment at {clip_current_time:.2f}s - {clip_current_time + audio_duration:.2f}s")
                    
                    # Advance clip_current_time by the actual clip duration
                    clip_current_time += audio_duration
                        
                except Exception as e:
                    logger.error(f"❌ Error processing scene {scene['scene_number']}: {type(e).__name__}: {str(e)}")
                    logger.error(f"  Scene details - has video_clip_url: {bool(video_clip_url)}, is_pocketrag: {is_pocketrag_scene}")
                    logger.error(f"  Stack trace:", exc_info=True)
                    audio_clip.close()  # Clean up before skipping
                    continue

            timings['clip_creation'] = time.time() - start_clips
            
            if not clips:
                logger.error("❌ FATAL: No valid clips generated - cannot create video")
                logger.error(f"  Total scenes in storyboard: {len(storyboard_project['storyboards'])}")
                audio_count = sum(1 for s in storyboard_project['storyboards'] if os.path.exists(os.path.join(audio_dir, f"scene_{s['scene_number']}.mp3")))
                logger.error(f"  Audio files found: {audio_count}")
                return None
            
            logger.info(f"Total clips generated: {len(clips)}")
            logger.info(f"Timing - Audio generation: {timings['audio_generation']:.2f}s, Clip creation: {timings['clip_creation']:.2f}s")

            # Add closing screen
            start_closing = time.time()
            if progress_callback:
                await progress_callback(0.60, "Creating closing screen...")
            
            try:
                closing_screen = self.create_closing_screen(duration=4)
                if closing_screen:
                    clips.append(closing_screen)
                    logger.info("Added closing screen with logos to video")
                else:
                    logger.warning("⚠️ Failed to create closing screen, continuing without it")
            except Exception as e:
                logger.error(f"⚠️ Error creating closing screen: {type(e).__name__}: {str(e)}")
                logger.error("Continuing without closing screen")
            
            timings['closing_screen'] = time.time() - start_closing
            
            # Add audio fadeout to last scene clip to prevent audio artifacts
            if len(clips) > 1 and clips[-2].audio is not None:
                clips[-2] = clips[-2].audio_fadeout(0.3)
            
            if progress_callback:
                await progress_callback(0.70, "Combining clips...")
            
            start_concat = time.time()
            try:
                logger.info(f"Concatenating {len(clips)} clips...")
                final_clip = concatenate_videoclips(clips, method="compose")
                timings['concatenation'] = time.time() - start_concat
                logger.info(f"✅ Clips concatenated successfully in {timings['concatenation']:.2f}s")
            except Exception as e:
                logger.error(f"❌ FATAL: Failed to concatenate clips: {type(e).__name__}: {str(e)}")
                logger.error(f"  Stack trace:", exc_info=True)
                raise
            
            # Use a separate thread for video writing to avoid blocking the event loop
            # Optimized settings: faster preset, lower fps for speed
            start_encoding = time.time()
            if progress_callback:
                await progress_callback(0.80, "Encoding video...")
            
            try:
                logger.info(f"Starting video encoding to: {video_path}")
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
                logger.info(f"✅ Video encoding completed in {timings['video_encoding']:.2f}s")
                
                # Verify the video file was created
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"Video file was not created at: {video_path}")
                
                file_size = os.path.getsize(video_path) / (1024 * 1024)
                logger.info(f"✅ Video file created: {file_size:.2f} MB")
                
            except Exception as e:
                logger.error(f"❌ FATAL: Video encoding failed: {type(e).__name__}: {str(e)}")
                logger.error(f"  Stack trace:", exc_info=True)
                raise

            start_captions = time.time()
            if progress_callback:
                await progress_callback(0.90, "Adding captions...")
            
            logger.info(f"🎯 Starting caption addition phase at 90% progress")
            logger.info(f"  Total subtitle segments: {len(subtitle_segments)}")
            logger.info(f"  Video path: {video_path}")
            logger.info(f"  Caption font: {caption_font}")
            
            subtitle_video_path = video_path.replace('.mp4', '_subtitle.mp4')
            logger.info(f"  Target subtitle video: {subtitle_video_path}")
            
            try:
                await self.add_captions(video_path, subtitle_video_path, caption_font, custom_segments=subtitle_segments, progress_callback=progress_callback)
                timings['caption_generation'] = time.time() - start_captions
                logger.info(f"✅ Caption generation completed in {timings['caption_generation']:.2f}s")
            except Exception as caption_error:
                logger.error(f"❌ FATAL: Caption generation failed: {type(caption_error).__name__}: {str(caption_error)}")
                logger.error(f"  Stack trace:", exc_info=True)
                raise
            
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
            logger.error(f"❌ CRITICAL ERROR in generate_video: {type(e).__name__}: {str(e)}")
            logger.error(f"Error details:", exc_info=True)
            logger.error(f"Current timing breakdown so far:")
            for key, value in timings.items():
                logger.error(f"  {key}: {value:.2f}s")
            logger.error(f"Number of clips created: {len(clips)}")
            logger.error(f"Number of subtitle segments: {len(subtitle_segments)}")
            return None
