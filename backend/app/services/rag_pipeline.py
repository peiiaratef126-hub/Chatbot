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
    - Sub-millisecond greeting fast-path
    - Multi-tool calling (Semantic KB Search, Order Checker, Human Escalation)
    - Strict max_iterations = 2 bound
    - Server-Sent Events (SSE) streaming with live citations and performance metrics
    """

    def __init__(self, vector_service: Optional[VectorService] = None, llm_service: Optional[LLMService] = None):
        self.settings = get_settings()
        self.vector_service = vector_service or get_vector_service()
        self.llm_service = llm_service or get_llm_service()

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
        Executes the ReAct RAG generation pipeline and yields formatted SSE data payloads.
        Format: data: {"type": "...", ...}\n\n
        """
        start_time = time.perf_counter()
        user_message = request.message.strip()
        brand = request.brand
        history = request.history
        
        # 1. Fast-Path Greeting Detection
        if self.llm_service.is_trivial_greeting(user_message):
            logger.info("Routing request to sub-millisecond greeting fast-path.")
            
            # Emit fast-path thought event
            thought_ev = StreamEvent(
                type="thought",
                content="Intent recognized as standard greeting. Executing direct fast-path response."
            )
            yield f"data: {thought_ev.model_dump_json()}\n\n"

            token_count = 0
            async for token in self.llm_service.stream_fastpath_greeting(brand=brand):
                token_count += 1
                token_ev = StreamEvent(type="token", token=token)
                yield f"data: {token_ev.model_dump_json()}\n\n"

            elapsed = (time.perf_counter() - start_time) * 1000
            metrics_ev = StreamEvent(
                type="metrics",
                metrics={
                    "latency_ms": round(elapsed, 1),
                    "tokens_per_sec": round(token_count / (elapsed / 1000) if elapsed > 0 else 300, 1),
                    "sources_count": 0,
                    "fast_path": True,
                    "iterations": 0
                }
            )
            yield f"data: {metrics_ev.model_dump_json()}\n\n"
            yield f"data: {StreamEvent(type='done', done=True).model_dump_json()}\n\n"
            return

        # 2. Agentic ReAct Reasoning Loop (Bounded by max_iterations = 2)
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

                # Execute vector search
                citations = await self.vector_service.search(
                    query=user_message,
                    brand=brand,
                    top_k=self.settings.TOP_K,
                    score_threshold=self.settings.SCORE_THRESHOLD
                )

                tool_result_ev = StreamEvent(
                    type="tool_result",
                    tool="knowledge_base_search",
                    output={"matches_found": len(citations), "top_score": citations[0].score if citations else 0.0}
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
                    yield f"data: {StreamEvent(type='tool_result', tool='escalate_to_human', output=esc_res).model_dump_json()}\n\n"
                    tool_observations.append(f"Escalation Dispatch Details:\n{json.dumps(esc_res, indent=2)}")

                # Ready to synthesize final answer
                break

        # 3. Final Answer Synthesis & Token Streaming
        yield f"data: {StreamEvent(type='thought', content='Synthesizing grounded response from verified context.').model_dump_json()}\n\n"

        prompt_messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_RAG_PROMPT}
        ]

        # Add history
        for hist in history[-4:]:
            prompt_messages.append({"role": hist.role, "content": hist.content})

        # Add context observations
        grounded_context = "\n\n".join(tool_observations) if tool_observations else "No specific knowledge base matches found."
        prompt_messages.append({
            "role": "user",
            "content": f"Customer Inquiry: {user_message}\n\nVerified Grounding Context:\n{grounded_context}\n\nPlease provide your helpful, accurate response:"
        })

        token_count = 0
        async for token in self.llm_service.stream_chat_completion(prompt_messages):
            token_count += 1
            yield f"data: {StreamEvent(type='token', token=token).model_dump_json()}\n\n"

        # 4. Final Performance Metrics Event
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
                "backend": self.vector_service.backend_type
            }
        )
        yield f"data: {metrics_ev.model_dump_json()}\n\n"

        # 5. Done Event
        yield f"data: {StreamEvent(type='done', done=True).model_dump_json()}\n\n"

_rag_pipeline_instance: Optional[RAGPipeline] = None

def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = RAGPipeline()
    return _rag_pipeline_instance
