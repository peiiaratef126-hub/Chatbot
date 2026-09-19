"""
End-to-End Live Production Verification Suite for SupportRAG
Validates all cloud endpoints, latency metrics, and agentic tools against the live deployment.
"""

import json
import sys
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://frontend-opal-delta-yz5oct1bu2.vercel.app"

def test_live_landing_page():
    print("[*] Probing Root Landing Page...")
    req = urllib.request.Request(BASE_URL, headers={"User-Agent": "SupportRAG-Auditor/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        body = resp.read().decode("utf-8")
        assert "SupportRAG" in body or "Customer Support RAG" in body
        print("  [OK] Root page live and accessible (HTTP 200).")

def test_live_health_endpoint():
    print("[*] Probing /api/health...")
    url = f"{BASE_URL}/api/health"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("status") == "healthy"
        assert "vector_db_backend" in data
        assert data.get("indexed_documents_count", 0) > 0
        print(f"  [OK] /api/health healthy. Backend: {data.get('vector_db_backend')}, Docs: {data.get('indexed_documents_count')}")

def test_live_kb_sample_endpoint():
    print("[*] Probing /api/kb/sample...")
    url = f"{BASE_URL}/api/kb/sample"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("total", 0) >= 100
        assert len(data.get("brands", [])) >= 6
        assert len(data.get("sample_articles", [])) > 0
        print(f"  [OK] /api/kb/sample verified. Total: {data.get('total')}, Brands: {len(data.get('brands'))}")

def test_live_chat_fastpath_greeting():
    print("[*] Testing Live Chat Fast-Path Greeting...")
    url = f"{BASE_URL}/api/chat"
    payload = json.dumps({
        "message": "Hello!",
        "history": [],
        "brand": "AppleSupport"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    start_time = time.perf_counter()
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        elapsed = (time.perf_counter() - start_time) * 1000
        assert "fast-path" in body or "thought" in body
        assert "AppleSupport" in body
        print(f"  [OK] Greeting fast-path streamed in {elapsed:.1f}ms.")

def test_live_chat_order_tracking():
    print("[*] Testing Live Chat Order Tracking Tool...")
    url = f"{BASE_URL}/api/chat"
    payload = json.dumps({
        "message": "Where is my package #ORDER-882194?",
        "history": [],
        "brand": "AmazonHelp"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        assert ("check_order_status" in body or "order_status_checker" in body), "Order tool not found in stream"
        assert "882194" in body
        assert "UPS" in body
        print("  [OK] Order tracking tool executed and streamed successfully.")

def test_live_chat_human_escalation():
    print("[*] Testing Live Chat Human Escalation Tool...")
    url = f"{BASE_URL}/api/chat"
    payload = json.dumps({
        "message": "I demand to speak with a human supervisor immediately!",
        "history": [],
        "brand": "Uber_Support"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        assert "escalate_to_human" in body
        assert "ESC-" in body
        print("  [OK] Human escalation tool executed and ticket generated.")

def test_live_cors_preflight():
    print("[*] Testing Live CORS Preflight OPTIONS...")
    url = f"{BASE_URL}/api/chat"
    req = urllib.request.Request(
        url,
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST"
        },
        method="OPTIONS"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 204 or resp.status == 200
        headers = dict(resp.getheaders())
        assert any(k.lower() == "access-control-allow-origin" for k in headers)
        print("  [OK] CORS preflight verified.")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Running SupportRAG Live Production Verification Suite")
    print(f"Target: {BASE_URL}")
    print("=" * 60)
    test_live_landing_page()
    test_live_health_endpoint()
    test_live_kb_sample_endpoint()
    test_live_cors_preflight()
    test_live_chat_fastpath_greeting()
    test_live_chat_order_tracking()
    test_live_chat_human_escalation()
    print("=" * 60)
    print("✅ ALL LIVE PRODUCTION INTEGRATION TESTS PASSED 100%!")
    print("=" * 60)
