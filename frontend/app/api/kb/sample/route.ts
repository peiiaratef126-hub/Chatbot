import { NextResponse } from "next/server";
import sampleKbArticles from "@/data/sample_kb.json";

export const dynamic = "force-dynamic";

export async function GET() {
  const brands = Array.from(new Set(sampleKbArticles.map((d) => d.brand))).sort();

  return NextResponse.json({
    total: sampleKbArticles.length,
    brands,
    sample_articles: sampleKbArticles.slice(0, 12).map((d) => ({
      doc_id: d.doc_id,
      brand: d.brand,
      category: d.category,
      query: d.query,
      resolution: d.resolution,
      score: 1.0,
    })),
  });
}
