import re
import logging
from typing import Tuple, List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("chatbot.guardrails")

class GuardrailResult(BaseModel):
    """Encapsulates outcome of PII sanitation and prompt injection inspection."""
    sanitized_message: str
    is_blocked: bool = False
    block_reason: Optional[str] = None
    safe_response: Optional[str] = None
    redactions: List[str] = []

class GuardrailsService:
    """
    Production-grade Input Guardrails & PII Sanitizer.
    Zero external cost, regex and heuristic-based safety validation.
    """

    # 1. PII Patterns
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

    # 2. Prompt Injection & Jailbreak Patterns
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

    def evaluate(self, message: str) -> GuardrailResult:
        """
        Evaluates input through full guardrail stack:
        1. Injection and jailbreak defense
        2. PII masking and data sanitization
        """
        # Step 1: Detect adversarial injection
        is_injection, reason = self.detect_prompt_injection(message)
        if is_injection:
            return GuardrailResult(
                sanitized_message=message,
                is_blocked=True,
                block_reason=reason,
                safe_response=self.SAFE_REJECTION_RESPONSE,
                redactions=[]
            )

        # Step 2: Sanitize sensitive customer PII
        sanitized_msg, detected_pii = self.sanitize_pii(message)
        if detected_pii:
            logger.info(f"Guardrail sanitized PII in customer message: {detected_pii}")

        return GuardrailResult(
            sanitized_message=sanitized_msg,
            is_blocked=False,
            block_reason=None,
            safe_response=None,
            redactions=detected_pii
        )

_guardrails_instance: Optional[GuardrailsService] = None

def get_guardrails_service() -> GuardrailsService:
    global _guardrails_instance
    if _guardrails_instance is None:
        _guardrails_instance = GuardrailsService()
    return _guardrails_instance
