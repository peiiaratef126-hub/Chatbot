import { NextResponse } from "next/server";
import sampleKbArticles from "@/data/sample_kb.json";

export const dynamic = "force-dynamic";

const startTime = Date.now();

export async function GET() {
  const hasGroq = Boolean(process.env.GROQ_API_KEY);
  const uptime = (Date.now() - startTime) / 1000;

  const qdrantUrl = process.env.QDRANT_URL?.replace(/\/+$/, "");
  const qdrantApiKey = process.env.QDRANT_API_KEY;
  const qdrantCollection = process.env.QDRANT_COLLECTION || "customer_support_kb";

  let vectorDbConnected = false;
  let vectorDbBackend = "in_memory_sample_kb";
  let indexedDocsCount = sampleKbArticles.length;

  if (qdrantUrl && qdrantApiKey) {
    try {
      const res = await fetch(`${qdrantUrl}/collections/${qdrantCollection}`, {
        headers: {
          "api-key": qdrantApiKey,
        },
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "ok" && data.result) {
          vectorDbConnected = true;
          vectorDbBackend = "qdrant_cloud";
          indexedDocsCount = data.result.points_count ?? sampleKbArticles.length;
        }
      }
    } catch {
      // Graceful fallback to sample KB
    }
  }

  return NextResponse.json(
    {
      status: "healthy",
      version: "1.0.0",
      environment: process.env.NODE_ENV || "production",
      mock_mode: !hasGroq,
      groq_model: process.env.GROQ_MODEL || "llama-3.1-8b-instant",
      vector_db_connected: vectorDbConnected,
      vector_db_backend: vectorDbBackend,
      indexed_documents_count: indexedDocsCount,
      uptime_seconds: Math.round(uptime * 100) / 100,
    },
    {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
      },
    }
  );
}
