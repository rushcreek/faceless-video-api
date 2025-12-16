import os
import asyncio
from cartesia import Cartesia
from app.core.config import settings
from app.core.logging import logger

class AudioGenerator:
    def __init__(self, client=None):
        # client parameter kept for backward compatibility but not used
        self.cartesia_client = Cartesia(api_key=settings.CARTESIA_API_KEY)
        self.speech_rate = settings.tts.get('speech_rate', 1.0)  # Default to 1.0 if not found
        # Build voice mapping from config
        self.cartesia_voices = {v['id']: v['cartesia_id'] for v in settings.voices}

    async def generate_audio(self, text: str, output_file: str, voice_name: str) -> bool:
        try:
            # Get Cartesia voice ID from voice name using config
            if settings.voices and len(settings.voices) > 0:
                default_voice = settings.voices[0]['cartesia_id']
            else:
                default_voice = "79a125e8-cd45-4c13-8a67-188112f4dd22"  # Fallback
            voice_id = self.cartesia_voices.get(voice_name, default_voice)
            
            # Run synchronous Cartesia API in thread pool
            await asyncio.to_thread(self._generate_audio_sync, text, output_file, voice_id)
            
            logger.info(f"Speech synthesized for text [{text}], and the audio was saved to [{output_file}]")
            return True

        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            return False
    
    def _generate_audio_sync(self, text: str, output_file: str, voice_id: str):
        """Synchronous helper to generate audio with Cartesia"""
        chunk_iter = self.cartesia_client.tts.bytes(
            model_id="sonic-3",
            transcript=text,
            voice={
                "mode": "id",
                "id": voice_id,
            },
            output_format={
                "container": "mp3",
                "sample_rate": 44100,
                "encoding": "mp3",
            },
            language="en",
            speed=self.speech_rate
        )
        
        with open(output_file, "wb") as f:
            for chunk in chunk_iter:
                f.write(chunk)

   
