import os
import logging
from openai import AsyncOpenAI

logger = logging.getLogger("agent.llm")

SYSTEM_PROMPT = (
    "You are a helpful assistant for children. Speak English exclusively. "
    "IMPORTANT: Keep your answers very concise and brief. "
    "Never use more than 2 sentences."
)


class LLM:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = "google/gemini-3.1-flash-lite"

    async def generate(self, messages: list[dict]) -> str:
        """Send chat history to LLM and return the response text."""
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        logger.info(f"Sending {len(messages)} messages to LLM...")
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
        )
        content = resp.choices[0].message.content
        logger.info(f"LLM response: {content[:80]}...")
        return content
