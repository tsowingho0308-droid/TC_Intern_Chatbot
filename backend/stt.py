import json
import logging
import asyncio
import os
import urllib.parse

import websockets

logger = logging.getLogger("agent.stt")

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class StreamingTranscriber:
    """Manages a Deepgram streaming listen WebSocket for real-time STT."""

    def __init__(self):
        self._ws = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._listener: asyncio.Task | None = None
        self._running = False
        self._api_key = os.getenv("DEEPGRAM_API_KEY")

    def _build_url(self) -> str:
        params = {
            "model": "nova-3",
            "language": "en",
            "encoding": "linear16",
            "sample_rate": "16000",
            "interim_results": "true",
        }
        return f"{DEEPGRAM_WS_URL}?{urllib.parse.urlencode(params)}"

    async def connect(self):
        """Open a new Deepgram streaming connection."""
        await self._cleanup()
        self._queue = asyncio.Queue()

        url = self._build_url()
        self._ws = await websockets.connect(
            url,
            additional_headers={"Authorization": f"Token {self._api_key}"},
        )
        self._running = True
        self._listener = asyncio.create_task(self._listen_loop())
        logger.info("Deepgram streaming connection opened")

    async def _cleanup(self):
        """Close existing connection and cancel listener."""
        self._running = False
        if self._listener:
            self._listener.cancel()
            try:
                await self._listener
            except (asyncio.CancelledError, Exception):
                pass
            self._listener = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def _listen_loop(self):
        try:
            async for raw in self._ws:
                if not self._running:
                    break
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") != "Results":
                    continue
                try:
                    transcript = msg["channel"]["alternatives"][0]["transcript"]
                except (KeyError, IndexError):
                    continue
                is_final = bool(
                    msg.get("is_final") or msg.get("from_finalize")
                )
                if transcript:
                    await self._queue.put((transcript, is_final))
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            if self._running:
                logger.error(f"Deepgram listener error: {e}")

    async def send_audio(self, chunk: bytes):
        if self._ws and self._running:
            try:
                await self._ws.send(chunk)
            except websockets.ConnectionClosed:
                pass

    async def finalize(self) -> str:
        """Signal end of speech and collect the final transcript."""
        if not self._ws:
            return ""
        try:
            await self._ws.send(json.dumps({"type": "Finalize"}))
        except websockets.ConnectionClosed:
            return ""

        final_text = ""
        try:
            while True:
                text, is_final = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                if is_final:
                    final_text = text
                    break
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for final transcript")

        logger.info(f"STT: {final_text[:80]}")
        return final_text

    async def close(self):
        await self._cleanup()
        logger.info("Deepgram streaming connection closed")
