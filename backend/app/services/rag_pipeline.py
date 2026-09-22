import asyncio
import json
import logging
import re
import time
from typing import AsyncGenerator, Dict, Any, List, Optional

from app.config import get_settings
from app.schemas.chat import (
    ChatRequest,
    ChatMessage,
    KnowledgeCitation,
    StreamEvent
)
from app.services.vector_service import VectorService, get_vector_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.guardrails import GuardrailsService, get_guardrails_service
from app.services.session_service import SessionService, get_session_service

logger = logging.getLogger("chatbot.rag_pipeline")

SYSTEM_RAG_PROMPT = """You are an expert enterprise customer support specialist.
Answer the customer's question authoritatively, politely, and concisely using the provided verified Knowledge Base articles and tool observations.
Rules:
1. Base your answer strictly on the verified knowledge base and tool outputs. Do NOT hallucinate policies or fake phone numbers.
2. If instructions from the knowledge base apply, provide step-by-step guidance clearly.
3. If an order status or escalation tool was executed, clearly reference the status or ticket ID to reassure the customer.
4. Maintain a warm, empathetic, and professional brand tone.
"""

class RAGPipeline:
    """
    Orchestrates an Agentic RAG / ReAct Loop with:
    - Safety Input Guardrails & PII Sanitizer (Milestone 2)
    - Session Persistence & Multi-Turn History (Milestone 3)
    - Sub-millisecond greeting fast-path
    - Hybrid Knowledge Base Search + FlashRank Cross-Encoder Reranker (Milestone 1)
    - Corrective RAG (CRAG) & Query Rewriting fallback (Milestone 6)
    - Multi-tool calling (Semantic KB Search, Order Checker, Human Escalation)
    - Strict max_iterations = 2 bound
    - Server-Sent Events (SSE) streaming with live citations and performance metrics
    """

    def __init__(
        self,
        vector_service: Optional[VectorService] = None,
        llm_service: Optional[LLMService] = None,
        guardrails_service: Optional[GuardrailsService] = None,
        session_service: Optional[SessionService] = None
    ):
        self.settings = get_settings()
        self.vector_service = vector_service or get_vector_service()
        self.llm_service = llm_service or get_llm_service()
        self.guardrails_service = guardrails_service or get_guardrails_service()
        self.session_service = session_service or get_session_service()

    def _execute_order_status_tool(self, identifier: str) -> Dict[str, Any]:
        """Simulates an enterprise ERP / logistics order tracking tool."""
        clean_id = identifier.strip().upper()
        return {
            "order_id": clean_id,
            "status": "In Transit - Out for Delivery",
            "carrier": "UPS Expedited",
            "estimated_delivery": "Today by 7:00 PM",
            "last_scan_location": "Local Carrier Facility",
            "signature_required": False
        }

    def _execute_escalation_tool(self, reason: str, brand: Optional[str] = None) -> Dict[str, Any]:
        """Simulates enterprise CRM ticket creation and sentiment-based human escalation."""
        ticket_id = f"ESC-{int(time.time() * 1000) % 1000000:06d}"
        return {
            "ticket_id": ticket_id,
            "brand": brand or "Enterprise",
            "queue": "Tier 2 Senior Resolution Specialist",
            "priority": "High",
            "estimated_wait_time": "3-5 minutes",
            "status": "Assigned to Human Agent"
        }

    async def execute_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Executes the full Guardrails -> CRAG -> ReAct -> Session persistence pipeline.
        Yields formatted SSE data payloads: data: {"type": "...", ...}\n\n
        """
        start_time = time.perf_counter()
        raw_message = request.message.strip()
        brand = request.brand
        history = request.history

        # 0. Session Persistence Initialization (Milestone 3)
        session_id = await self.session_service.get_or_create_session(
            session_id=request.session_id,
            brand=brand
        )
        # Emit active session event
        yield f"data: {StreamEvent(type='session', session_id=session_id).model_dump_json()}\n\n"

        # 1. Safety Guardrails & PII Sanitization (Milestone 2)
        user_message = raw_message
        if getattr(self.settings, "ENABLE_GUARDRAILS", True):
            guard_eval = self.guardrails_service.evaluate(raw_message)

            if guard_eval.is_blocked:
                # System prompt injection / jailbreak attempted
                yield f"data: {StreamEvent(type='guardrail', content=f'Policy restriction: {guard_eval.block_reason}').model_dump_json()}\n\n"
                yield f"data: {StreamEvent(type='thought', content='Blocked harmful system directive or prompt injection attempt.').model_dump_json()}\n\n"

                # Stream safe rejection response directly
                safe_text = guard_eval.safe_response or "I cannot fulfill this request due to enterprise safety policies."
                for word in safe_text.split(" "):
                    yield f"data: {StreamEvent(type='token', token=word + ' ').model_dump_json()}\n\n"
                    await asyncio.sleep(0.01)

                elapsed = (time.perf_counter() - start_time) * 1000
                yield f"data: {StreamEvent(type='metrics', metrics={'latency_ms': round(elapsed, 1), 'tokens_per_sec': 100, 'guardrail_blocked': True}).model_dump_json()}\n\n"
                yield f"data: {StreamEvent(type='done', done=True).model_dump_json()}\n\n"

                # Persist messages
                await self.session_service.save_message(session_id, "user", raw_message, message_id=request.message_id)
                await self.session_service.save_message(session_id, "assistant", safe_text)
                return

            if guard_eval.redactions:
                yield f"data: {StreamEvent(type='guardrail', content=f'Sanitized sensitive customer data: {', '.join(guard_eval.redactions)}').model_dump_json()}\n\n"
                user_message = guard_eval.sanitized_message

        # Persist sanitized user message
        await self.session_service.save_message(
            session_id=session_id,
            role="user",
            content=user_message,
            message_id=request.message_id
        )

        # 2. Fast-Path Greeting Detection
        if self.llm_service.is_trivial_greeting(user_message):
            logger.info("Routing request to sub-millisecond greeting fast-path.")
            yield f"data: {StreamEvent(type='thought', content='Intent recognized as standard greeting. Executing direct fast-path response.').model_dump_json()}\n\n"

            greeting_tokens: List[str] = []
            async for token in self.llm_service.stream_fastpath_greeting(brand=brand):
                greeting_tokens.append(token)
                yield f"data: {StreamEvent(type='token', token=token).model_dump_json()}\n\n"

            elapsed = (time.perf_counter() - start_time) * 1000
            metrics_ev = StreamEvent(
                type="metrics",
                metrics={
                    "latency_ms": round(elapsed, 1),
                    "tokens_per_sec": round(len(greeting_tokens) / (elapsed / 1000) if elapsed > 0 else 300, 1),
                    "sources_count": 0,
                    "fast_path": True,
                    "iterations": 0,
                    "session_id": session_id
                }
            )
            yield f"data: {metrics_ev.model_dump_json()}\n\n"
            yield f"data: {StreamEvent(type='done', done=True).model_dump_json()}\n\n"

            # Persist assistant greeting
            await self.session_service.save_message(
                session_id=session_id,
                role="assistant",
                content="".join(greeting_tokens)
            )
            return

        # 3. Agentic ReAct Reasoning Loop (Bounded by max_iterations = 2)
        citations: List[KnowledgeCitation] = []
        tool_observations: List[str] = []
        max_iterations = self.settings.MAX_REACT_ITERATIONS
        iteration = 0

        # Heuristic Intent Parsing for Tool Selection
        order_pattern = re.search(r'(?:order|tracking|pkg|shipment)\s*(?:#|id|number)?\s*[:#\-]?\s*([A-Za-z0-9\-_]{4,})|#([A-Za-z0-9\-_]{4,})', user_message, re.IGNORECASE)
        escalation_pattern = any(w in user_message.lower() for w in ["speak to human", "real person", "agent", "fraud", "unacceptable", "lawsuit", "manager"])

        while iteration < max_iterations:
            iteration += 1

            if iteration == 1:
                # Thought 1: Determine knowledge retrieval and tools
                thought_msg = f"Analyzing customer query for brand '{brand or 'All'}' to retrieve grounded knowledge."
                yield f"data: {StreamEvent(type='thought', content=thought_msg).model_dump_json()}\n\n"

                # Tool Call 1: Semantic Knowledge Base Search
                tool_call_ev = StreamEvent(
                    type="tool_call",
                    tool="knowledge_base_search",
                    input={"query": user_message, "brand": brand}
                )
                yield f"data: {tool_call_ev.model_dump_json()}\n\n"

                # Execute hybrid vector search + FlashRank reranking
                citations = await self.vector_service.search(
                    query=user_message,
                    brand=brand,
                    top_k=self.settings.TOP_K,
                    score_threshold=self.settings.SCORE_THRESHOLD
                )

                top_score = citations[0].score if citations else 0.0

                # Corrective RAG (CRAG) & Query Rewriting (Milestone 6)
                if getattr(self.settings, "ENABLE_CRAG", True) and (not citations or top_score < self.settings.CRAG_CONFIDENCE_THRESHOLD):
                    yield f"data: {StreamEvent(type='thought', content=f'Initial retrieval confidence low ({top_score:.2f} < {self.settings.CRAG_CONFIDENCE_THRESHOLD:.2f}). Triggering Corrective RAG (CRAG) query reformulation.').model_dump_json()}\n\n"
                    
                    rewritten_query = await self.llm_service.reformulate_query(user_message, brand=brand)
                    yield f"data: {StreamEvent(type='thought', content=f'CRAG reformulated query: \"{rewritten_query}\". Re-querying knowledge base.').model_dump_json()}\n\n"

                    crag_citations = await self.vector_service.search(
                        query=rewritten_query,
                        brand=brand,
                        top_k=self.settings.TOP_K,
                        score_threshold=0.35  # Relaxed threshold for CRAG re-query
                    )

                    crag_top_score = crag_citations[0].score if crag_citations else 0.0
                    if crag_top_score > top_score:
                        citations = crag_citations
                        top_score = crag_top_score
                        yield f"data: {StreamEvent(type='thought', content=f'CRAG search improved top retrieval confidence to {top_score:.2f}.').model_dump_json()}\n\n"
                    else:
                        yield f"data: {StreamEvent(type='thought', content='CRAG re-query complete. Proceeding with synthesized context.').model_dump_json()}\n\n"

                tool_result_ev = StreamEvent(
                    type="tool_result",
                    tool="knowledge_base_search",
                    output={"matches_found": len(citations), "top_score": top_score, "reranked": bool(citations and citations[0].reranked)}
                )
                yield f"data: {tool_result_ev.model_dump_json()}\n\n"

                # Emit individual citations to UI
                for cit in citations:
                    yield f"data: {StreamEvent(type='citation', citation=cit).model_dump_json()}\n\n"

                if citations:
                    kb_context = "\n".join(
                        f"[{c.brand} | {c.category}] Issue: {c.query} -> Solution: {c.resolution}"
                        for c in citations
                    )
                    tool_observations.append(f"Retrieved Knowledge Base Context:\n{kb_context}")

                # Check if secondary tool is triggered
                if order_pattern:
                    order_num = (order_pattern.group(1) or order_pattern.group(2)).lstrip("#-_")
                    yield f"data: {StreamEvent(type='thought', content=f'Detected order tracking request for ID {order_num}.').model_dump_json()}\n\n"
                    yield f"data: {StreamEvent(type='tool_call', tool='check_order_status', input={'order_id': order_num}).model_dump_json()}\n\n"
                    order_res = self._execute_order_status_tool(order_num)
                    yield f"data: {StreamEvent(type='tool_result', tool='check_order_status', output=order_res).model_dump_json()}\n\n"
                    tool_observations.append(f"Order Tracking Details:\n{json.dumps(order_res, indent=2)}")

                if escalation_pattern:
                    yield f"data: {StreamEvent(type='thought', content='High urgency or customer escalation request detected. Triggering tier-2 dispatch.').model_dump_json()}\n\n"
                    yield f"data: {StreamEvent(type='tool_call', tool='escalate_to_human', input={'reason': user_message[:50], 'brand': brand, 'urgency': 'high'}).model_dump_json()}\n\n"
                    esc_res = self._execute_escalation_tool(user_message, brand=brand)
                    try:
                        await self.session_service.save_escalation(
                            ticket_id=esc_res["ticket_id"],
                            session_id=session_id,
                            brand=esc_res["brand"],
                            query=user_message,
                            reason=user_message[:100],
                            urgency="High"
                        )
                    except Exception as e_esc:
                        logger.warning(f"Could not persist escalation to SQLite ({e_esc})")
                    yield f"data: {StreamEvent(type='tool_result', tool='escalate_to_human', output=esc_res).model_dump_json()}\n\n"
                    tool_observations.append(f"Escalation Dispatch Details:\n{json.dumps(esc_res, indent=2)}")

                # Ready to synthesize final answer
                break

        # 4. Final Answer Synthesis & Token Streaming
        yield f"data: {StreamEvent(type='thought', content='Synthesizing grounded response from verified context.').model_dump_json()}\n\n"

        prompt_messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_RAG_PROMPT}
        ]

        # Add multi-turn history
        for hist in history[-4:]:
            prompt_messages.append({"role": hist.role, "content": hist.content})

        # Add context observations
        grounded_context = "\n\n".join(tool_observations) if tool_observations else "No specific knowledge base matches found."
        prompt_messages.append({
            "role": "user",
            "content": f"Customer Inquiry: {user_message}\n\nVerified Grounding Context:\n{grounded_context}\n\nPlease provide your helpful, accurate response:"
        })

        token_count = 0
        response_tokens: List[str] = []
        async for token in self.llm_service.stream_chat_completion(prompt_messages):
            token_count += 1
            response_tokens.append(token)
            yield f"data: {StreamEvent(type='token', token=token).model_dump_json()}\n\n"

        # 5. Final Performance Metrics Event
        elapsed_total = (time.perf_counter() - start_time) * 1000
        tokens_per_sec = (token_count / (elapsed_total / 1000)) if elapsed_total > 0 else 300.0

        metrics_ev = StreamEvent(
            type="metrics",
            metrics={
                "latency_ms": round(elapsed_total, 1),
                "tokens_per_sec": round(tokens_per_sec, 1),
                "sources_count": len(citations),
                "confidence_score": citations[0].score if citations else 0.0,
                "iterations": iteration,
                "backend": self.vector_service.backend_type,
                "session_id": session_id,
                "reranked": bool(citations and citations[0].reranked)
            }
        )
        yield f"data: {metrics_ev.model_dump_json()}\n\n"

        # 6. Persist assistant response to session
        full_assistant_reply = "".join(response_tokens)
        await self.session_service.save_message(
            session_id=session_id,
            role="assistant",
            content=full_assistant_reply,
            citations=citations
        )

        # 7. Done Event
        yield f"data: {StreamEvent(type='done', done=True).model_dump_json()}\n\n"

_rag_pipeline_instance: Optional[RAGPipeline] = None

def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = RAGPipeline()
    return _rag_pipeline_instance
