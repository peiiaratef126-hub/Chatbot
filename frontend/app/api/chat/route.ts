import { NextRequest } from "next/server";
import { createRAGEventStream } from "@/lib/rag-engine";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const message = body.message || "";
    const history = body.history || [];
    const brand = body.brand || null;

    if (!message.trim()) {
      return new Response(JSON.stringify({ error: "Message cannot be empty" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const stream = createRAGEventStream(message, history, brand);

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
