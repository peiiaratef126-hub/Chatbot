"""
Domain-Anchored Agentic Alignment (DA3) - Synthetic Dataset Generator
Author: LoneVertex <minaalaa141@gmail.com>

Synthesizes high-quality, multi-turn agentic customer support dialogues grounded in
production tools (knowledge_base_search, check_order_status, escalate_to_human)
formatted in native Qwen 2.5 ChatML syntax.
"""

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("da3_generator")

# Default Tool Definitions in Qwen 2.5 ChatML format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "knowledge_base_search",
            "description": "Search the verified enterprise knowledge base for policies, setup instructions, and technical resolutions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query or issue description"},
                    "brand": {"type": "string", "description": "Brand scope: AppleSupport, AmazonHelp, Uber_Support, SpotifyCares, Delta, NikeSupport"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_order_status",
            "description": "Retrieve real-time logistics tracking and shipping status for an order or shipment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order or tracking identifier (e.g., ORD-99214, 1Z99999999)"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate high-priority issues, account lockouts, fraud, or angry customers to a human specialist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Concise justification for escalation"},
                    "brand": {"type": "string", "description": "Brand for ticket assignment"},
                    "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Urgency rating"}
                },
                "required": ["reason", "urgency"]
            }
        }
    }
]

SYSTEM_PROMPT = (
    "You are an expert customer support specialist equipped with tool access.\n"
    "You have access to the following tools:\n"
    "- knowledge_base_search(query: str, brand: Optional[str]): Retrieve verified support articles.\n"
    "- check_order_status(order_id: str): Look up shipment tracking details and delivery dates.\n"
    "- escalate_to_human(reason: str, urgency: str, brand: Optional[str]): Escalate urgent or sensitive issues.\n\n"
    "When a tool is needed, respond with a <tool_call> block containing valid JSON. "
    "Once tool output is provided, deliver a clear, empathetic, and actionable final resolution."
)

SAMPLE_CARRIERS = ["UPS Expedited", "FedEx Ground", "DHL Express", "USPS Priority"]
SAMPLE_STATUSES = [
    "In Transit - Out for Delivery",
    "In Transit - Arrived at Regional Facility",
    "Delivered - Left on Front Porch",
    "Exception - Address Correction Required"
]

def load_knowledge_base(kb_path: Path) -> List[Dict[str, Any]]:
    """Loads knowledge base articles from JSON."""
    if not kb_path.exists():
        logger.error(f"Knowledge base not found at: {kb_path}")
        return []
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_simulated_order_result(order_id: str) -> Dict[str, Any]:
    """Generates realistic order lookup tool response."""
    carrier = random.choice(SAMPLE_CARRIERS)
    status = random.choice(SAMPLE_STATUSES)
    days = random.randint(0, 3)
    deliv = "Today by 7:00 PM" if days == 0 else f"In {days} business days"
    return {
        "order_id": order_id.upper(),
        "status": status,
        "carrier": carrier,
        "estimated_delivery": deliv,
        "last_scan": f"Local Carrier Hub (scan #{random.randint(1000, 9999)})",
        "signature_required": random.choice([True, False])
    }

def generate_simulated_escalation_result(brand: str, reason: str, urgency: str) -> Dict[str, Any]:
    """Generates realistic human escalation tool response."""
    ticket_num = random.randint(100000, 999999)
    wait_time = "1-3 minutes" if urgency in ["high", "critical"] else "5-10 minutes"
    return {
        "ticket_id": f"ESC-{ticket_num}",
        "brand": brand,
        "priority": urgency.capitalize(),
        "queue": "Tier 2 Senior Resolution Specialist",
        "estimated_wait_time": wait_time,
        "status": "Assigned to Human Agent"
    }

def format_chatml_sample(messages: List[Dict[str, str]]) -> str:
    """Formats a list of message dicts into Qwen 2.5 ChatML text."""
    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    return "\n".join(parts)

class SyntheticGenerator:
    """Generates synthetic agentic training data via Groq or structured offline synthesizer."""

    def __init__(
        self,
        api_key: Optional[str],
        model: str = "qwen/qwen3.8-27b",
        concurrency: int = 3,
        kb_articles: Optional[List[Dict[str, Any]]] = None
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.kb_articles = kb_articles or []
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=30.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            } if self.api_key else {}
        )

    async def close(self):
        await self.client.aclose()

    async def synthesize_sample_with_groq(
        self,
        kb_entry: Dict[str, Any],
        archetype: str
    ) -> Optional[Dict[str, Any]]:
        """Invokes Groq API to produce a grounded conversational trace."""
        if not self.api_key:
            return None

        brand = kb_entry.get("brand", "Support")
        query = kb_entry.get("query", "")
        resolution = kb_entry.get("resolution", "")

        prompt_guidance = ""
        if archetype == "knowledge_base_search":
            prompt_guidance = (
                f"Create a realistic customer inquiry asking about: '{query}'.\n"
                f"Brand: {brand}.\n"
                f"Tool to invoke: knowledge_base_search with arguments query='{query}' and brand='{brand}'.\n"
                f"Tool observation to return: {json.dumps({'query': query, 'resolution': resolution})}\n"
                f"Final assistant answer must use the resolution and be empathetic and concise."
            )
        elif archetype == "check_order_status":
            order_id = f"ORD-{random.randint(10000, 99999)}"
            order_res = generate_simulated_order_result(order_id)
            prompt_guidance = (
                f"Create a realistic customer inquiry asking for tracking of order '{order_id}'.\n"
                f"Brand: {brand}.\n"
                f"Tool to invoke: check_order_status with argument order_id='{order_id}'.\n"
                f"Tool observation to return: {json.dumps(order_res)}\n"
                f"Final assistant answer must report the carrier, delivery estimate, and status."
            )
        elif archetype == "escalate_to_human":
            esc_res = generate_simulated_escalation_result(brand, "Urgent account / billing issue", "high")
            prompt_guidance = (
                f"Create a frustrated customer inquiry requiring human supervisor escalation for {brand} "
                f"regarding '{query}' with severe urgency.\n"
                f"Tool to invoke: escalate_to_human with arguments reason='Urgent customer dispute', urgency='high', brand='{brand}'.\n"
                f"Tool observation to return: {json.dumps(esc_res)}\n"
                f"Final assistant answer must provide the ticket ID and reassure the customer."
            )
        else:
            # Multi-tool
            order_id = f"ORD-{random.randint(10000, 99999)}"
            order_res = generate_simulated_order_result(order_id)
            prompt_guidance = (
                f"Create a customer inquiry that mentions order '{order_id}' and asks about: '{query}'.\n"
                f"Brand: {brand}.\n"
                f"Tool to invoke: check_order_status or knowledge_base_search.\n"
                f"Tool observation: {json.dumps(order_res)}\n"
                f"Final assistant answer must address the tracking status and policy."
            )

        system_instruction = (
            "You are a synthetic dataset generator producing JSON objects. Output ONLY a valid JSON object with key 'dialogue'.\n"
            "The JSON structure must be:\n"
            "{\n"
            '  "user_message": "...",\n'
            '  "tool_call": {"name": "...", "arguments": {...}},\n'
            '  "tool_result": {...},\n'
            '  "final_assistant_message": "..."\n'
            "}"
        )

        async with self.semaphore:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    resp = await self.client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": prompt_guidance}
                            ],
                            "response_format": {"type": "json_object"},
                            "temperature": 0.7,
                            "max_tokens": 800
                        }
                    )
                    if resp.status_code == 429:
                        wait = (attempt + 1) * 2.5
                        logger.warning(f"Rate limited by Groq API (429). Retrying in {wait:.1f}s...")
                        await asyncio.sleep(wait)
                        continue
                    if resp.status_code != 200:
                        logger.warning(f"Groq API error {resp.status_code}: {resp.text[:120]}")
                        await asyncio.sleep(1.0)
                        continue

                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)

                    # Extract fields
                    u_msg = parsed.get("user_message") or parsed.get("dialogue", {}).get("user_message")
                    t_call = parsed.get("tool_call") or parsed.get("dialogue", {}).get("tool_call")
                    t_res = parsed.get("tool_result") or parsed.get("dialogue", {}).get("tool_result")
                    a_msg = parsed.get("final_assistant_message") or parsed.get("dialogue", {}).get("final_assistant_message")

                    if not (u_msg and t_call and a_msg):
                        continue

                    # Validate tool call format
                    tool_call_str = f"<tool_call>\n{json.dumps(t_call)}\n</tool_call>"
                    tool_result_str = json.dumps(t_res or {})

                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": u_msg},
                        {"role": "assistant", "content": tool_call_str},
                        {"role": "tool", "content": tool_result_str},
                        {"role": "assistant", "content": a_msg}
                    ]

                    return {
                        "messages": messages,
                        "text": format_chatml_sample(messages),
                        "archetype": archetype,
                        "brand": brand,
                        "source": "groq_synthetic"
                    }

                except Exception as e:
                    logger.debug(f"Attempt {attempt+1} failed: {e}")
                    await asyncio.sleep(1.0)

        return None

    def synthesize_offline_sample(
        self,
        kb_entry: Dict[str, Any],
        archetype: str
    ) -> Dict[str, Any]:
        """High-quality deterministic template-based synthesizer for offline generation or fill-in."""
        brand = kb_entry.get("brand", "Support")
        query = kb_entry.get("query", "")
        resolution = kb_entry.get("resolution", "")
        category = kb_entry.get("category", "General")

        greetings = [
            f"Hi @{brand},",
            f"Hello {brand} support,",
            f"Hey team,",
            f"Can someone help me at @{brand}?"
        ]
        greet = random.choice(greetings)

        if archetype == "knowledge_base_search":
            user_questions = [
                f"{greet} I have an issue: {query}. How do I resolve this?",
                f"{greet} {query}. Is there an official guide or fix for this?",
                f"{greet} Quick question regarding {category}: {query}."
            ]
            u_msg = random.choice(user_questions)
            t_call = {
                "name": "knowledge_base_search",
                "arguments": {"query": query, "brand": brand}
            }
            t_res = {"brand": brand, "category": category, "query": query, "resolution": resolution}
            a_msg = (
                f"Hello! Thank you for reaching out to **{brand} Support**.\n\n"
                f"Here is the recommended resolution for this issue:\n"
                f"{resolution}\n\n"
                "Please let me know if you need additional assistance or further troubleshooting!"
            )

        elif archetype == "check_order_status":
            order_id = f"ORD-{random.randint(10000, 99999)}"
            order_res = generate_simulated_order_result(order_id)
            user_questions = [
                f"{greet} Where is order #{order_id}? It was supposed to arrive today.",
                f"{greet} Can you check the delivery status for tracking #{order_id}?",
                f"{greet} Haven't received my package yet, reference #{order_id}."
            ]
            u_msg = random.choice(user_questions)
            t_call = {
                "name": "check_order_status",
                "arguments": {"order_id": order_id}
            }
            t_res = order_res
            a_msg = (
                f"I've checked the latest logistics status for order **#{order_id}**.\n\n"
                f"- **Current Status**: {order_res['status']}\n"
                f"- **Carrier**: {order_res['carrier']}\n"
                f"- **Estimated Delivery**: {order_res['estimated_delivery']}\n"
                f"- **Last Scan**: {order_res['last_scan']}\n\n"
                "If you require signature coordination or an address update, feel free to let me know!"
            )

        elif archetype == "escalate_to_human":
            urgencies = ["high", "critical"]
            urgency = random.choice(urgencies)
            esc_res = generate_simulated_escalation_result(brand, query, urgency)
            user_questions = [
                f"{greet} This is unacceptable! {query}. I demand to speak to a human supervisor immediately!",
                f"{greet} Urgent security/billing alert: {query}. Transfer me to a live agent right now.",
                f"{greet} None of the automated steps worked for {query}. Please escalate this case."
            ]
            u_msg = random.choice(user_questions)
            t_call = {
                "name": "escalate_to_human",
                "arguments": {"reason": f"Urgent customer dispute: {query[:60]}", "brand": brand, "urgency": urgency}
            }
            t_res = esc_res
            a_msg = (
                f"I completely understand your frustration, and I am prioritizing your case immediately.\n\n"
                f"I have created an escalated priority dispatch ticket:\n"
                f"- **Ticket ID**: {esc_res['ticket_id']}\n"
                f"- **Assigned Queue**: {esc_res['queue']}\n"
                f"- **Priority**: {esc_res['priority']}\n"
                f"- **Estimated Wait Time**: {esc_res['estimated_wait_time']}\n\n"
                "A senior specialist has been notified and will connect with you shortly."
            )

        else:
            # Multi-tool composite
            order_id = f"ORD-{random.randint(10000, 99999)}"
            order_res = generate_simulated_order_result(order_id)
            u_msg = f"{greet} I ordered item #{order_id} but also need help: {query}."
            t_call = {
                "name": "check_order_status",
                "arguments": {"order_id": order_id}
            }
            t_res = order_res
            a_msg = (
                f"I've verified your order **#{order_id}** ({order_res['status']}, scheduled for {order_res['estimated_delivery']}).\n\n"
                f"Regarding your inquiry ({query}):\n{resolution}\n\n"
                "Let me know if you need anything else!"
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": u_msg},
            {"role": "assistant", "content": f"<tool_call>\n{json.dumps(t_call)}\n</tool_call>"},
            {"role": "tool", "content": json.dumps(t_res)},
            {"role": "assistant", "content": a_msg}
        ]

        return {
            "messages": messages,
            "text": format_chatml_sample(messages),
            "archetype": archetype,
            "brand": brand,
            "source": "offline_synthesizer"
        }

async def generate_dataset(
    target_count: int,
    output_path: Path,
    kb_path: Path,
    api_key: Optional[str] = None,
    concurrency: int = 3,
    model: str = "qwen/qwen3.8-27b",
    offline_only: bool = False
):
    """Main generation loop with resume support."""
    kb_articles = load_knowledge_base(kb_path)
    if not kb_articles:
        logger.error("Cannot proceed without knowledge base articles.")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing_samples: List[Dict[str, Any]] = []

    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        existing_samples.append(json.loads(line))
                    except Exception:
                        pass
        logger.info(f"Loaded {len(existing_samples)} existing samples from {output_path.name}. Resuming...")

    needed = target_count - len(existing_samples)
    if needed <= 0:
        logger.info(f"Target count of {target_count} already reached! ({len(existing_samples)} available)")
        return

    logger.info(f"Generating {needed} samples to reach target {target_count}...")
    generator = SyntheticGenerator(
        api_key=api_key,
        model=model,
        concurrency=concurrency,
        kb_articles=kb_articles
    )

    archetypes = [
        "knowledge_base_search",
        "knowledge_base_search",  # 40% KB search
        "check_order_status",      # 30% Order lookup
        "escalate_to_human",      # 20% Escalation
        "multi_tool"              # 10% Composite
    ]

    generated_count = 0
    with open(output_path, "a", encoding="utf-8") as f:
        while (len(existing_samples) + generated_count) < target_count:
            batch_size = min(20, target_count - (len(existing_samples) + generated_count))
            tasks = []

            for _ in range(batch_size):
                kb_entry = random.choice(kb_articles)
                archetype = random.choice(archetypes)
                if offline_only or not generator.api_key:
                    sample = generator.synthesize_offline_sample(kb_entry, archetype)
                    f.write(json.dumps(sample) + "\n")
                    f.flush()
                    generated_count += 1
                else:
                    tasks.append(generator.synthesize_sample_with_groq(kb_entry, archetype))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, dict) and res:
                        f.write(json.dumps(res) + "\n")
                        f.flush()
                        generated_count += 1
                    else:
                        # Fall back to offline synthesis on API hiccup to guarantee progress
                        kb_entry = random.choice(kb_articles)
                        archetype = random.choice(archetypes)
                        fallback_sample = generator.synthesize_offline_sample(kb_entry, archetype)
                        f.write(json.dumps(fallback_sample) + "\n")
                        f.flush()
                        generated_count += 1

            total_now = len(existing_samples) + generated_count
            if total_now % 50 == 0 or total_now >= target_count:
                logger.info(f"Progress: {total_now}/{target_count} samples generated ({total_now/target_count*100:.1f}%)")

    await generator.close()
    logger.info(f"Generation complete! Total dataset size: {len(existing_samples) + generated_count} at {output_path}")

def main():
    parser = argparse.ArgumentParser(description="DA3 Synthetic Agentic Dataset Generator")
    parser.add_argument("--count", type=int, default=5400, help="Target number of samples (60 percent = 5400)")
    parser.add_argument("--output", type=str, default="data/da3_synthetic_tool_use_5400.jsonl", help="Output file path")
    parser.add_argument("--kb", type=str, default="scripts/data/sample_kb.json", help="Knowledge base JSON path")
    parser.add_argument("--api-key", type=str, default=os.getenv("GROQ_API_KEY", ""), help="Groq Cloud API Key")
    parser.add_argument("--model", type=str, default="qwen/qwen3.8-27b", help="Groq model for generation")
    parser.add_argument("--concurrency", type=int, default=3, help="Concurrent async API calls")
    parser.add_argument("--offline-only", action="store_true", help="Force offline deterministic synthesis")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    output_file = project_root / args.output
    kb_file = project_root / args.kb

    asyncio.run(generate_dataset(
        target_count=args.count,
        output_path=output_file,
        kb_path=kb_file,
        api_key=args.api_key,
        concurrency=args.concurrency,
        model=args.model,
        offline_only=args.offline_only
    ))

if __name__ == "__main__":
    main()
