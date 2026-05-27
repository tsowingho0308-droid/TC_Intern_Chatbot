import logging
from backend.llm import LLM
from backend.tts import TTS

logger = logging.getLogger("agent.core")


class VoiceAgent:
    def __init__(self, tts: TTS):
        self.llm = LLM()
        self.tts = tts
        self.chat_history: list[dict] = []
        self._tts_playing = False

    def interrupt(self):
        self._tts_playing = False
        logger.info("TTS interrupted by user")

    async def process_transcript(self, transcript: str) -> tuple[str, bytes]:
        """
        Run LLM + TTS on a transcript (STT is handled externally via streaming).
        Returns (response_text, tts_audio_bytes).
        """
        self.chat_history.append({"role": "user", "content": transcript})
        response_text = await self.llm.generate(self.chat_history)
        self.chat_history.append({"role": "assistant", "content": response_text})

        self._tts_playing = True
        audio = await self.tts.synthesize(response_text)
        self._tts_playing = False

        return response_text, audio

    @property
    def is_speaking(self) -> bool:
        return self._tts_playing
