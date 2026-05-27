import asyncio
import os
import logging
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, JobContext, WorkerOptions, cli
from livekit.plugins import openai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("my-agent")

async def entrypoint(ctx: JobContext):
    logger.info("Connecting to LiveKit room...")
    await ctx.connect()
    logger.info("Successfully connected!")

    # 1. LLM (特殊要求：繞道去 OpenRouter 找 Gemini)
    llm_brain = openai.LLM(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="google/gemini-3.1-flash-lite" 
    )

    # 2. STT (改用 OpenRouter API 路由)
    stt_ear = openai.STT(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="openai/whisper-1" 
    )

    # 3. TTS (改用 OpenRouter API 路由)
    tts_voice = openai.TTS(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="openai/tts-1" 
    )

    # 4. Agent 組裝
    session = AgentSession(
        stt=stt_ear,
        llm=llm_brain,
        tts=tts_voice
    )

    # 5. 啟動 Agent
    await session.start(
        room=ctx.room,
        agent=Agent(instructions="You are a helpful assistant. Speak English exclusively.")
    )
    
    logger.info("Agent started!")
    
    # 6. 開場白
    await session.generate_reply(
        instructions="Say exactly this: 'Hello! I am online. How can I help you?'"
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))