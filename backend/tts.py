import logging
from deepgram import AsyncDeepgramClient

logger = logging.getLogger("agent.tts")


class TTS:
    def __init__(self, client: AsyncDeepgramClient):
        self.client = client

    async def synthesize(self, text: str) -> bytes:
        """Convert text to PCM audio bytes (16kHz mono 16-bit)."""
        chunks = []
        async for chunk in self.client.speak.v1.audio.generate(
            text=text,
            model="aura-asteria-en",
            encoding="linear16",
            sample_rate=16000,
        ):
            chunks.append(chunk)
        data = b"".join(chunks)
        logger.info(f"TTS synthesized {len(data)} bytes for: {text[:50]}...")
        return data
