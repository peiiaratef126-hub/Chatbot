---
title: Customer Support RAG Chatbot API
emoji: ⚡
colorFrom: green
colorTo: emerald
sdk: docker
app_port: 7860
pinned: false
---

# Customer Support RAG Chatbot Backend API

High-performance, production-ready FastAPI backend for the **Customer Support Agentic RAG Chatbot**.

- **Inference:** Groq Cloud API (`llama-3.1-8b-instant` streaming at ~300 tok/sec)
- **Agentic Loop:** Bounded ReAct reasoning (`max_iterations = 2`) with multi-tool calling
- **Retrieval:** Qdrant Cloud vector search with zero-setup in-memory fallback
- **Protocol:** Server-Sent Events (SSE) on `POST /api/chat`
- **Health & Telemetry:** Real-time metrics on `GET /api/health`
