import { NextResponse } from "next/server";
import sampleKbArticles from "@/data/sample_kb.json";

export const dynamic = "force-dynamic";

const startTime = Date.now();

export async function GET() {
  const hasGroq = Boolean(process.env.GROQ_API_KEY);
  const uptime = (Date.now() - startTime) / 1000;

  return NextResponse.json({
    status: "healthy",
    version: "1.0.0",
    environment: process.env.NODE_ENV || "production",
    mock_mode: !hasGroq,
    groq_model: process.env.GROQ_MODEL || "llama-3.1-8b-instant",
    vector_db_connected: false,
    vector_db_backend: "in_memory_sample_kb",
    indexed_documents_count: sampleKbArticles.length,
    uptime_seconds: Math.round(uptime * 100) / 100,
  });
}
