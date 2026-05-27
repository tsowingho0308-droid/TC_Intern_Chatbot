import asyncio
import json
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from deepgram import AsyncDeepgramClient

from backend.stt import StreamingTranscriber
from backend.tts import TTS

logger = logging.getLogger("agent.server")

app = FastAPI()
_agent = None
_dg_client = None
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


def get_dg_client() -> AsyncDeepgramClient:
    global _dg_client
    if _dg_client is None:
        _dg_client = AsyncDeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
    return _dg_client


def get_agent():
    global _agent
    if _agent is None:
        from backend.agent import VoiceAgent
        tts = TTS(client=get_dg_client())
        _agent = VoiceAgent(tts=tts)
    return _agent


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket client connected")

    audio_buffer = bytearray()
    is_busy = False
    pipeline_task: asyncio.Task | None = None

    transcriber = StreamingTranscriber()
    await transcriber.connect()

    async def send_audio(audio_bytes: bytes):
        chunk_size = 4096
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i : i + chunk_size]
            await ws.send_bytes(chunk)

    async def run_pipeline(transcript: str):
        """Send transcript, response, and TTS audio to the client."""
        nonlocal is_busy
        try:
            await ws.send_json({"type": "transcript", "text": transcript})
            response_text, tts_audio = await get_agent().process_transcript(transcript)
            if response_text:
                await ws.send_json({"type": "response", "text": response_text})
            if tts_audio:
                await ws.send_json({"type": "tts_start"})
                await send_audio(tts_audio)
                await ws.send_json({"type": "tts_done"})
        finally:
            is_busy = False
            audio_buffer.clear()
            try:
                await transcriber.connect()
            except Exception as e:
                logger.error(f"Failed to reopen transcriber: {e}")

    try:
        while True:
            data = await ws.receive()

            if data["type"] == "websocket.receive":
                if "text" in data:
                    msg = json.loads(data["text"])
                    msg_type = msg.get("type", "")

                    if msg_type == "end":
                        if len(audio_buffer) > 1600 and not is_busy:
                            audio_buffer.clear()
                            is_busy = True
                            transcript = await transcriber.finalize()
                            if transcript.strip():
                                pipeline_task = asyncio.create_task(run_pipeline(transcript))
                            else:
                                is_busy = False
                                await transcriber.connect()
                        elif is_busy:
                            logger.info("Pipeline busy, skipping end")
                        else:
                            logger.info("Audio too short, ignoring")

                    elif msg_type == "interrupt":
                        get_agent().interrupt()
                        if pipeline_task and not pipeline_task.done():
                            pipeline_task.cancel()
                        is_busy = False
                        audio_buffer.clear()

                    elif msg_type == "reset":
                        get_agent().chat_history.clear()
                        await ws.send_json({"type": "reset_done"})

                elif "bytes" in data:
                    chunk = data["bytes"]
                    audio_buffer.extend(chunk)
                    if not is_busy:
                        try:
                            await transcriber.send_audio(chunk)
                        except Exception:
                            pass

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await transcriber.close()
        logger.info("WebSocket connection closed")


# Mount static files
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
