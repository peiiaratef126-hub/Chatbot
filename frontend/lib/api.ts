export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface KnowledgeCitation {
  doc_id: number | string;
  brand: string;
  category: string;
  query: string;
  resolution: string;
  score: number;
  reranked?: boolean;
}

export interface ToolTrace {
  tool: string;
  input?: Record<string, any>;
  output?: Record<string, any>;
}

export interface PerformanceMetrics {
  latency_ms: number;
  tokens_per_sec: number;
  sources_count: number;
  confidence_score?: number;
  iterations?: number;
  backend?: string;
  fast_path?: boolean;
  session_id?: string;
  reranked?: boolean;
}

export interface HealthData {
  status: string;
  version: string;
  environment: string;
  mock_mode: boolean;
  groq_model: string;
  vector_db_connected: boolean;
  vector_db_backend: string;
  indexed_documents_count: number;
  uptime_seconds: number;
}

export interface EscalationItem {
  ticket_id: string;
  session_id?: string;
  brand: string;
  query: string;
  reason: string;
  urgency: string;
  language?: string;
  created_at: string;
}

export interface FeedbackItem {
  id?: number;
  session_id: string;
  message_id: string;
  rating: "up" | "down";
  comment?: string;
  created_at: string;
}

export interface ChatStreamCallbacks {
  onSession?: (sessionId: string) => void;
  onGuardrail?: (notice: string) => void;
  onThought?: (content: string) => void;
  onToolCall?: (tool: string, input: any) => void;
  onToolResult?: (tool: string, output: any) => void;
  onCitation?: (citation: KnowledgeCitation) => void;
  onToken?: (token: string) => void;
  onMetrics?: (metrics: PerformanceMetrics) => void;
  onError?: (err: string) => void;
  onDone?: () => void;
}

function createTimeoutSignal(ms: number): AbortSignal {
  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
    return AbortSignal.timeout(ms);
  }
  const controller = new AbortController();
  setTimeout(() => controller.abort(), ms);
  return controller.signal;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchHealth(): Promise<HealthData | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: createTimeoutSignal(5000),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchSampleArticles(): Promise<KnowledgeCitation[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/kb/sample`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: createTimeoutSignal(5000),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.sample_articles || [];
  } catch {
    return [];
  }
}

export async function streamChatMessage(
  message: string,
  history: ChatMessage[],
  brand: string | null,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
  sessionId?: string | null,
  language?: string | null
): Promise<void> {
  const url = `${API_BASE_URL}/api/chat`;
  
  const payload = {
    message,
    history: history.map((m) => ({ role: m.role, content: m.content })),
    brand: brand && brand !== "All Brands" ? brand : null,
    session_id: sessionId || null,
    language: language || null,
    stream: true,
  };

  const activeSignal = signal || createTimeoutSignal(30000);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
    signal: activeSignal,
  });

  if (!response.ok || !response.body) {
    const errorText = await response.text().catch(() => "Unknown server error");
    throw new Error(`Chat API request failed (${response.status}): ${errorText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let doneEmitted = false;

  const emitDone = () => {
    if (!doneEmitted) {
      doneEmitted = true;
      callbacks.onDone?.();
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const event of events) {
        const lines = event.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;

            try {
              const parsed = JSON.parse(dataStr);
              switch (parsed.type) {
                case "session":
                  if (parsed.session_id) {
                    callbacks.onSession?.(parsed.session_id);
                  }
                  break;
                case "guardrail":
                  callbacks.onGuardrail?.(parsed.content || "Safety policy applied.");
                  break;
                case "thought":
                  callbacks.onThought?.(parsed.content || "");
                  break;
                case "tool_call":
                  callbacks.onToolCall?.(parsed.tool, parsed.input);
                  break;
                case "tool_result":
                  callbacks.onToolResult?.(parsed.tool, parsed.output);
                  break;
                case "citation":
                  if (parsed.citation) {
                    callbacks.onCitation?.(parsed.citation);
                  }
                  break;
                case "token":
                  callbacks.onToken?.(parsed.token || "");
                  break;
                case "metrics":
                  if (parsed.metrics) {
                    callbacks.onMetrics?.(parsed.metrics);
                  }
                  break;
                case "error":
                  callbacks.onError?.(parsed.content || "An error occurred");
                  break;
                case "done":
                  emitDone();
                  break;
              }
            } catch (err) {
              console.warn("Failed to parse SSE JSON payload:", dataStr, err);
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
    emitDone();
  }
}

export async function submitFeedback(payload: {
  session_id: string;
  message_id: string;
  rating: "up" | "down";
  comment?: string;
}): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/chat/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchEscalations(limit: number = 50): Promise<EscalationItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/escalations?limit=${limit}`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.escalations || [];
  } catch {
    return [];
  }
}

export async function fetchFeedback(negativeOnly: boolean = false, limit: number = 50): Promise<FeedbackItem[]> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/admin/feedback?negative_only=${negativeOnly}&limit=${limit}`,
      {
        headers: { Accept: "application/json" },
        cache: "no-store",
      }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.feedback || [];
  } catch {
    return [];
  }
}
