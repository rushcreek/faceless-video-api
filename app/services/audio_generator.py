import os
import asyncio
from cartesia import Cartesia
from app.core.config import settings
from app.core.logging import logger

# Cartesia voice ID mapping
CARTESIA_VOICES = {
    "barbershop-man": "a0e99841-438c-4a64-b679-ae501e7d6091",
    "calm-lady": "79a125e8-cd45-4c13-8a67-188112f4dd22",
    "female-conversational": "f9836c6e-a0bd-460e-9d3c-f7299fa60f94",
    "female-narrator": "c5e3e3ab-0929-4f03-b4ca-7c3b7d5aaec1",
    "male-conversational": "95856005-0332-41b0-935f-352e296aa0df",
    "male-narrator": "84f5e7d6-e4b3-4fc2-8f88-01b9e1e1c3be",
    "friendly-sidekick": "42b39f37-515f-4eee-8546-73e841679c1d"
}

class AudioGenerator:
    def __init__(self, client=None):
        # client parameter kept for backward compatibility but not used
        self.cartesia_client = Cartesia(api_key=settings.CARTESIA_API_KEY)
        self.speech_rate = settings.tts.get('speech_rate', 1.0)  # Default to 1.0 if not found

    async def generate_audio(self, text: str, output_file: str, voice_name: str) -> bool:
        try:
            # Get Cartesia voice ID from voice name
            voice_id = CARTESIA_VOICES.get(voice_name, CARTESIA_VOICES["female-narrator"])
            
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

   
