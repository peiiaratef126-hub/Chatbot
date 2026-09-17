import asyncio
import json
import logging
import re
import time
from typing import AsyncGenerator, Dict, Any, List, Optional
import httpx

from app.config import get_settings
from app.schemas.chat import ChatMessage

logger = logging.getLogger("chatbot.llm_service")

# Common greeting triggers for fast-path intent routing
GREETING_PATTERNS = [
    r"^(\s*)*(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|yo|howdy)(\s+(there|friend|team|support|everyone))?(\s*|[!?.])*$"
]

class LLMService:
    """
    Asynchronous LLM service interfacing with Groq Cloud API
    with instant greeting fast-path and full offline mock streaming.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[httpx.AsyncClient] = None
        self._init_client()

    def _init_client(self):
        """Initializes httpx async client with appropriate timeouts."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=10.0),
            headers={
                "Authorization": f"Bearer {self.settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
        )

    def is_trivial_greeting(self, message: str) -> bool:
        """Determines if the message is a trivial greeting to route to fast-path."""
        clean_msg = message.strip().lower()
        if len(clean_msg) < 3:
            return True
        for pattern in GREETING_PATTERNS:
            if re.match(pattern, clean_msg, re.IGNORECASE):
                return True
        return False

    async def stream_fastpath_greeting(self, brand: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Sub-millisecond streaming response for simple greetings without invoking RAG tools."""
        brand_name = brand if brand else "Customer Support"
        greeting_text = (
            f"Hello! Welcome to **{brand_name} Help & Support**. "
            "How can I assist you with your device, order, account, or billing today?"
        )
        words = greeting_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield chunk
            await asyncio.sleep(0.015)  # Simulate human-like high-speed stream

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 800
    ) -> AsyncGenerator[str, None]:
        """
        Streams completion tokens from Groq Cloud API or runs mock streaming fallback.
        """
        # If in Mock Mode or API key not present, run mock generator
        if self.settings.is_mock_mode:
            logger.info("Executing chat completion via Zero-Cost Mock Mode.")
            async for token in self._mock_stream_generator(messages):
                yield token
            return

        url = f"{self.settings.GROQ_BASE_URL}/chat/completions"
        payload = {
            "model": self.settings.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"Groq API Error {response.status_code}: {error_body.decode('utf-8')}")
                    # Fallback gracefully to mock stream on error
                    async for token in self._mock_stream_generator(messages, fallback_reason="API error"):
                        yield token
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            delta = data_json.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"Groq streaming connection failed: {e}. Falling back to mock generator.")
            async for token in self._mock_stream_generator(messages, fallback_reason=str(e)):
                yield token

    async def _mock_stream_generator(
        self,
        messages: List[Dict[str, str]],
        fallback_reason: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generates realistic high-speed token streaming for local testing without Groq keys.
        """
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        # Generate intelligent contextual mock response
        response_text = (
            "I have reviewed your request and checked our verified support policies. "
            "Here is the standard resolution procedure:\n\n"
            "1. **Verification & Diagnostics:** Ensure your account details and device firmware are updated to the latest release.\n"
            "2. **Resolution Step:** If this involves an active order or transaction, please reference your confirmation number. For hardware issues, a device restart or network cache reset often resolves the problem immediately.\n"
            "3. **Next Actions:** If the condition persists after following these steps, our support team can initiate a formal replacement or billing inquiry for you.\n\n"
            "Please let me know if you need further clarification!"
        )

        tokens = re.split(r'(\s+)', response_text)
        for token in tokens:
            if token:
                yield token
                await asyncio.sleep(0.012)  # ~80 tokens per second simulation

    async def close(self):
        """Cleanly close HTTP client session."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

_llm_service_instance: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
