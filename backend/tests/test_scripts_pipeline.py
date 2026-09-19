import sys
from pathlib import Path
import pytest

# Ensure scripts directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_da3_dataset import format_chatml_text, generate_bitext_support_samples
from scripts.generate_agentic_dataset import SyntheticGenerator

def test_format_chatml_text():
    """Verify ChatML conversion encloses roles with <|im_start|> and <|im_end|>."""
    messages = [
        {"role": "system", "content": "System directive."},
        {"role": "user", "content": "Customer query."},
        {"role": "assistant", "content": "Support response."}
    ]
    chatml = format_chatml_text(messages)
    assert "<|im_start|>system\nSystem directive.<|im_end|>" in chatml
    assert "<|im_start|>user\nCustomer query.<|im_end|>" in chatml
    assert "<|im_start|>assistant\nSupport response.<|im_end|>" in chatml

def test_generate_bitext_support_samples():
    """Verify Bitext sample generator returns requested sample count with ChatML messages."""
    samples = generate_bitext_support_samples(target_count=10)
    assert len(samples) == 10
    for s in samples:
        assert "messages" in s
        assert "text" in s
        assert len(s["messages"]) == 3
        assert s["messages"][0]["role"] == "system"
        assert s["messages"][1]["role"] == "user"
        assert s["messages"][2]["role"] == "assistant"
        assert "<|im_start|>" in s["text"]

def test_synthetic_generator_offline_archetypes():
    """Verify SyntheticGenerator creates valid tool calls for all archetypes."""
    kb_article = {
        "doc_id": 1,
        "brand": "AppleSupport",
        "category": "Technical Support",
        "query": "iPhone battery drains rapidly",
        "resolution": "Check Settings > Battery and optimize Background App Refresh."
    }
    generator = SyntheticGenerator(api_key=None, kb_articles=[kb_article])

    # Test KB search archetype
    sample_kb = generator.synthesize_offline_sample(kb_article, archetype="knowledge_base_search")
    assert "messages" in sample_kb
    assert any("<tool_call>" in m["content"] for m in sample_kb["messages"])
    assert any("knowledge_base_search" in m["content"] for m in sample_kb["messages"])

    # Test Order Status archetype
    sample_order = generator.synthesize_offline_sample(kb_article, archetype="check_order_status")
    assert any("check_order_status" in m["content"] for m in sample_order["messages"])

    # Test Escalation archetype
    sample_esc = generator.synthesize_offline_sample(kb_article, archetype="escalate_to_human")
    assert any("escalate_to_human" in m["content"] for m in sample_esc["messages"])
