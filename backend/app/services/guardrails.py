import re
import logging
from typing import Tuple, List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("chatbot.guardrails")

class GuardrailResult(BaseModel):
    """Encapsulates outcome of PII sanitation, prompt injection inspection, and language enforcement."""
    sanitized_message: str
    is_blocked: bool = False
    block_reason: Optional[str] = None
    safe_response: Optional[str] = None
    detected_language: str = "en"
    is_supported_language: bool = True
    redactions: List[str] = []

class GuardrailsService:
    """
    Production-grade Input Guardrails, PII Sanitizer & Strict Bilingual Enforcer.
    Zero external cost, regex and heuristic-based safety validation.
    """

    # 1. Supported Languages Whitelist
    SUPPORTED_LANGUAGES = {"ar", "en"}

    UNSUPPORTED_LANGUAGE_RESPONSE = (
        "عذراً، الدعم الفني متوفر حالياً باللغتين العربية والإنجليزية فقط. يرجى كتابة استفسارك بإحدى هاتين اللغتين.\n"
        "Sorry, customer support is currently available in Arabic and English only. Please submit your inquiry in either language."
    )

    # Common English words and brand tokens for robust whitelist filtering
    ENGLISH_COMMON_WORDS = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with",
        "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
        "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
        "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just", "him",
        "know", "take", "people", "into", "year", "your", "good", "some", "could", "them", "see", "other", "than",
        "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", "how",
        "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
        "hello", "hi", "hey", "support", "help", "order", "status", "cancel", "refund", "return", "shipping", "shipment",
        "delivery", "package", "item", "iphone", "apple", "amazon", "uber", "spotify", "delta", "nike", "flight", "battery",
        "screen", "charge", "card", "account", "password", "email", "reset", "problem", "issue", "track", "tracking", "arrived",
        "device", "drains", "rapidly", "yesterday", "today", "tomorrow", "money", "received", "purchased", "transit"
    }

    # Distinct non-English/non-Arabic European vocabulary
    FOREIGN_COMMON_WORDS = {
        "bonjour", "salut", "merci", "svp", "mon", "ma", "mes", "votre", "vos", "avec", "pour", "suis", "est", "cassé", "casse", "probleme",
        "hola", "gracias", "por", "favor", "roto", "puedo", "ayuda", "dónde", "está", "pedido", "cuenta", "buenos", "dias",
        "hallo", "bitte", "danke", "mein", "meine", "nicht", "kaputt", "hilfe", "wo", "ist", "guten", "tag",
        "ciao", "grazie", "dove", "olá", "obrigado", "obrigada", "bom", "dia", "boa", "tarde"
    }

    # 2. PII Patterns
    CARD_REGEX = re.compile(
        r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|'
        r'3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|'
        r'(?:2131|1800|35\d{3})\d{11}|(?:[0-9]{4}[-\s]?){3}[0-9]{4})\b'
    )
    PHONE_REGEX = re.compile(
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|'
        r'\b\+?20[-.\s]?1[0-25]\d{8}\b'
    )
    SSN_REGEX = re.compile(
        r'\b\d{3}-\d{2}-\d{4}\b|\b\d{14}\b'
    )
    SECRET_REGEX = re.compile(
        r'(?i)\b(password|passwd|secret|api[_-]?key|bearer)\s*[:=]\s*([^\s,;]+)'
    )

    # 3. Prompt Injection & Jailbreak Patterns
    INJECTION_PATTERNS = [
        re.compile(r'(?i)ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions'),
        re.compile(r'(?i)disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:rules|instructions|prompts)'),
        re.compile(r'(?i)reveal\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)'),
        re.compile(r'(?i)what\s+(?:is|are)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)'),
        re.compile(r'(?i)print\s+(?:your|the)\s+(?:system\s+)?(?:prompt|initial\s+instructions)'),
        re.compile(r'(?i)you\s+are\s+now\s+(?:in\s+)?(?:dan|developer|jailbreak|unrestricted)\s+mode'),
        re.compile(r'(?i)bypass\s+(?:your\s+)?(?:safety|guardrails|ethical\s+guidelines)'),
        re.compile(r'(?i)system\s+prompt\s+extraction'),
        re.compile(r'(?i)act\s+as\s+an\s+unrestricted\s+ai'),
        re.compile(r'(?i)override\s+(?:all\s+)?system\s+directives'),
    ]

    SAFE_REJECTION_RESPONSE = (
        "I am an automated customer support specialist operating on verified enterprise knowledge bases. "
        "For security and privacy, I cannot disclose system prompts, modify internal policies, or execute "
        "arbitrary directives. How may I assist you with your orders, products, or support account today?"
    )

    def sanitize_pii(self, text: str) -> Tuple[str, List[str]]:
        """
        Masks credit cards, phone numbers, SSNs, and passwords with redaction tokens.
        """
        redacted = text
        detected: List[str] = []

        if self.CARD_REGEX.search(redacted):
            redacted = self.CARD_REGEX.sub("[REDACTED_CARD]", redacted)
            detected.append("credit_card")

        if self.SSN_REGEX.search(redacted):
            redacted = self.SSN_REGEX.sub("[REDACTED_SSN]", redacted)
            detected.append("national_id_ssn")

        if self.PHONE_REGEX.search(redacted):
            redacted = self.PHONE_REGEX.sub("[REDACTED_PHONE]", redacted)
            detected.append("phone_number")

        if self.SECRET_REGEX.search(redacted):
            redacted = self.SECRET_REGEX.sub(r"\1: [REDACTED_SECRET]", redacted)
            detected.append("credentials_secret")

        return redacted, detected

    def detect_prompt_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Scans input for prompt extraction and jailbreak signatures.
        """
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(text):
                matched = pattern.pattern
                logger.warning(f"Guardrail triggered: prompt injection signature detected ({matched}).")
                return True, "system_prompt_extraction_or_jailbreak"
        return False, None

    def detect_language(self, text: str) -> Tuple[str, bool]:
        """
        Detects language and enforces strict bilingual policy (Arabic and English only).
        Returns (language_code, is_supported).
        """
        # 1. Arabic Unicode script detection
        arabic_chars = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text))
        cyrillic_chars = len(re.findall(r'[\u0400-\u04FF]', text))
        cjk_chars = len(re.findall(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', text))

        if arabic_chars >= 2 or (arabic_chars > 0 and len(text.strip()) <= 12):
            return "ar", True

        # Non-Latin, non-Arabic foreign scripts
        if cyrillic_chars >= 2:
            return "ru", False
        if cjk_chars >= 1:
            return "zh", False

        # 2. Latin word analysis
        words = [w.lower() for w in re.findall(r'[a-zA-Z\u00C0-\u00FF]{2,}', text)]
        if not words:
            return "en", True

        # Check explicit foreign words
        foreign_matches = [w for w in words if w in self.FOREIGN_COMMON_WORDS]
        if foreign_matches:
            return "other", False

        # Check European accented characters (é, è, ê, à, ç, ü, ö, ä, ß, ñ, etc.)
        has_accents = bool(re.search(r'[éèêëàâäçùûüîïôöñß¿¡]', text, re.IGNORECASE))
        if has_accents:
            return "other", False

        # Check English vocabulary
        english_matches = [w for w in words if w in self.ENGLISH_COMMON_WORDS]
        if len(english_matches) >= 1:
            return "en", True

        # If very short query with no foreign indicators, assume English
        if len(words) <= 2:
            return "en", True

        # Fallback to langdetect
        try:
            from langdetect import detect
            lang = detect(text)
            if lang in self.SUPPORTED_LANGUAGES:
                return lang, True
            return lang, False
        except Exception:
            return "en", True

    def evaluate(self, message: str, check_language: bool = True) -> GuardrailResult:
        """
        Evaluates input through full guardrail stack:
        1. Injection and jailbreak defense
        2. Strict bilingual support (Arabic & English Only)
        3. PII masking and data sanitization
        """
        # Step 1: Detect adversarial injection
        is_injection, reason = self.detect_prompt_injection(message)
        if is_injection:
            return GuardrailResult(
                sanitized_message=message,
                is_blocked=True,
                block_reason=reason,
                safe_response=self.SAFE_REJECTION_RESPONSE,
                detected_language="en",
                is_supported_language=True,
                redactions=[]
            )

        # Step 2: Strict Bilingual Support (Arabic & English Only - Milestone 1)
        detected_lang, is_supported = self.detect_language(message)
        if check_language and not is_supported:
            logger.info(f"Guardrail rejected unsupported language '{detected_lang}' for message: {message[:40]}")
            return GuardrailResult(
                sanitized_message=message,
                is_blocked=True,
                block_reason="unsupported_language",
                safe_response=self.UNSUPPORTED_LANGUAGE_RESPONSE,
                detected_language=detected_lang,
                is_supported_language=False,
                redactions=[]
            )

        # Step 3: Sanitize sensitive customer PII
        sanitized_msg, detected_pii = self.sanitize_pii(message)
        if detected_pii:
            logger.info(f"Guardrail sanitized PII in customer message: {detected_pii}")

        return GuardrailResult(
            sanitized_message=sanitized_msg,
            is_blocked=False,
            block_reason=None,
            safe_response=None,
            detected_language=detected_lang,
            is_supported_language=True,
            redactions=detected_pii
        )

_guardrails_instance: Optional[GuardrailsService] = None

def get_guardrails_service() -> GuardrailsService:
    global _guardrails_instance
    if _guardrails_instance is None:
        _guardrails_instance = GuardrailsService()
    return _guardrails_instance
