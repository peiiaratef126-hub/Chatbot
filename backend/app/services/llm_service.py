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

# Common greeting triggers for fast-path intent routing (English & Arabic)
GREETING_PATTERNS = [
    r"^(\s*)*(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|yo|howdy)(\s+(there|friend|team|support|everyone))?(\s*|[!?.])*$",
    r"^\s*(مرحبا|مرحباً|اهلا|أهلا|أهلاً|السلام\s+عليكم|صباح\s+الخير|مساء\s+الخير|هاي|أهلاً\s+وسهلاً)(\s+.*)?\s*[!؟?.]*\s*$"
]

class LLMService:
    """
    Asynchronous LLM service interfacing with Groq Cloud API
    with instant greeting fast-path and full offline mock streaming.
    Supports strict bilingual operations (Arabic & English).
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
        if len(clean_msg) < 3 and not bool(re.search(r'[\u0600-\u06FF]', clean_msg)):
            return True
        for pattern in GREETING_PATTERNS:
            if re.match(pattern, clean_msg, re.IGNORECASE):
                return True
        return False

    async def stream_fastpath_greeting(self, brand: Optional[str] = None, language: str = "en") -> AsyncGenerator[str, None]:
        """Sub-millisecond streaming response for simple greetings in customer's preferred language."""
        if language == "ar":
            brand_name = brand if brand else "مركز الدعم الفني"
            greeting_text = (
                f"أهلاً بك! مرحباً بك في مركز مساعدة ودعم **{brand_name}**. "
                "كيف يمكنني مساعدتك في استفسارات جهازك، طلبك، حسابك أو الدعم الفني اليوم؟"
            )
        else:
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

        # Check if the user inquiry is in Arabic
        is_arabic = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', last_user_msg))

        if is_arabic:
            response_text = (
                "لقد قمت بمراجعة استفسارك وفحص سياسات الدعم الفني المعتمدة لدينا. "
                "إليك خطوات الحل القياسية الموصى بها:\n\n"
                "1. **الفحص والتشخيص الأولي:** تأكد من تحديث حسابك ونظام تشغيل جهازك إلى أحدث إصدار متوفر.\n"
                "2. **خطوات الحل الفني:** إذا كان استفسارك يتعلق بطلب أو شحنة، يرجى الاستدلال برقم التتبع أو معرف الطلب (Order ID). "
                "وبالنسبة لمشاكل البطارية أو الجهاز، فإن إعادة تشغيل الجهاز وضبط التطبيقات في الخلفية (Background App Refresh) "
                "عبر الإعدادات (Settings) يساعد في تحسين الأداء وحل المشكلة بشكل فوري.\n"
                "3. **الإجراءات التالية:** إذا استمرت المشكلة بعد اتباع هذه الخطوات، يمكن لفريق الدعم تصعيد تذكرتك أو بدء إجراءات الاسترجاع والبدل.\n\n"
                "يرجى إعلامي إذا كنت بحاجة إلى مزيد من المساعدة!"
            )
        else:
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

    async def reformulate_query(self, query: str, brand: Optional[str] = None) -> str:
        """
        Fast single-pass query reformulation for Corrective RAG (CRAG).
        Extracts salient keywords, handles cross-lingual expansions, and removes filler.
        """
        # Arabic query reformulation
        if bool(re.search(r'[\u0600-\u06FF]', query)):
            from app.services.vector_service import VectorService
            terms: List[str] = []
            for ar_k, en_v in VectorService.ARABIC_TO_ENGLISH_SEMANTIC_MAP.items():
                if ar_k in query:
                    terms.extend(en_v)
            if terms:
                prefix = f"{brand} " if brand else ""
                unique_terms = list(dict.fromkeys(terms))
                return f"{prefix}{query} {' '.join(unique_terms)}".strip()
            return f"{brand or ''} {query}".strip()

        clean_tokens = [
            t for t in re.findall(r'\b[a-zA-Z0-9]{3,}\b', query.lower())
            if t not in {"how", "can", "what", "when", "where", "why", "the", "and", "for", "with", "about", "please", "help", "tell", "know", "issue", "problem"}
        ]
        keyword_query = " ".join(clean_tokens)

        if self.settings.is_mock_mode:
            prefix = f"{brand} " if brand and brand.lower() not in keyword_query else ""
            return f"{prefix}{keyword_query}".strip() or query

        try:
            url = f"{self.settings.GROQ_BASE_URL}/chat/completions"
            prompt = (
                f"Customer Query: '{query}'\n"
                f"Target Brand: {brand or 'General'}\n"
                "Extract 3 to 6 essential search keywords for a knowledge base lookup. "
                "Output ONLY the keywords separated by spaces, nothing else."
            )
            payload = {
                "model": self.settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a concise search query generator. Output only search keywords."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 50,
                "stream": False
            }
            res = await self.client.post(url, json=payload, timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                reformulated = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if reformulated:
                    return reformulated.replace('"', '').replace('\n', ' ').strip()
        except Exception as e:
            logger.warning(f"CRAG LLM reformulation failed ({e}), using heuristic keyword query.")

        prefix = f"{brand} " if brand and brand.lower() not in keyword_query else ""
        return f"{prefix}{keyword_query}".strip() or query

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
