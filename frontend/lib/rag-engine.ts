import sampleKbArticles from "@/data/sample_kb.json";

export interface KnowledgeCitation {
  doc_id: number | string;
  brand: string;
  category: string;
  query: string;
  resolution: string;
  score: number;
}

export interface StreamEvent {
  type: "thought" | "tool_call" | "tool_result" | "citation" | "token" | "metrics" | "error" | "done";
  content?: string;
  tool?: string;
  input?: Record<string, any>;
  output?: Record<string, any>;
  citation?: KnowledgeCitation;
  token?: string;
  metrics?: Record<string, any>;
  done?: boolean;
}

const GREETING_REGEX = /^(\s*)*(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|yo|howdy)(\s+(there|friend|team|support|everyone))?(\s*|[!?.])*$/i;

export function isTrivialGreeting(message: string): boolean {
  const clean = message.trim().toLowerCase();
  if (clean.length < 3) return true;
  return GREETING_REGEX.test(clean);
}

function tokenize(text: string): string[] {
  return text.toLowerCase().match(/\b[a-z0-9]{2,}\b/g) || [];
}

function computeSimilarity(query: string, docText: string): number {
  const qTokens = tokenize(query);
  const dTokens = tokenize(docText);
  if (!qTokens.length || !dTokens.length) return 0.0;

  const qCounts: Record<string, number> = {};
  for (const t of qTokens) qCounts[t] = (qCounts[t] || 0) + 1;

  const dCounts: Record<string, number> = {};
  for (const t of dTokens) dCounts[t] = (dCounts[t] || 0) + 1;

  const intersection = Object.keys(qCounts).filter((t) => t in dCounts);
  if (!intersection.length) return 0.0;

  let dot = 0;
  for (const t of intersection) dot += qCounts[t] * dCounts[t];

  const qNorm = Math.sqrt(Object.values(qCounts).reduce((acc, c) => acc + c * c, 0));
  const dNorm = Math.sqrt(Object.values(dCounts).reduce((acc, c) => acc + c * c, 0));
  const cosine = dot / (qNorm * dNorm);
  const coverage = intersection.length / Object.keys(qCounts).length;
  const hybrid = 0.6 * cosine + 0.4 * coverage;
  return Math.min(0.99, hybrid);
}

export function searchKnowledgeBase(
  query: string,
  brand?: string | null,
  topK: number = 4,
  threshold: number = 0.40
): KnowledgeCitation[] {
  const scored: Array<{ score: number; doc: any }> = [];

  for (const doc of sampleKbArticles) {
    if (brand && brand !== "All Brands" && doc.brand.toLowerCase() !== brand.toLowerCase()) {
      continue;
    }

    const corpus = `${doc.brand} ${doc.category} ${doc.query} ${doc.resolution}`;
    let score = computeSimilarity(query, corpus);

    if (doc.brand.toLowerCase().includes(query.toLowerCase())) {
      score = Math.min(0.98, score + 0.15);
    }

    if (score >= threshold) {
      scored.push({ score, doc });
    }
  }

  scored.sort((a, b) => b.score - a.score);

  return scored.slice(0, topK).map(({ score, doc }) => ({
    doc_id: doc.doc_id,
    brand: doc.brand,
    category: doc.category,
    query: doc.query,
    resolution: doc.resolution,
    score: Math.round(score * 10000) / 10000,
  }));
}

export function executeOrderStatusTool(identifier: string) {
  return {
    order_id: identifier.toUpperCase(),
    status: "In Transit - Out for Delivery",
    carrier: "UPS Expedited",
    estimated_delivery: "Today by 7:00 PM",
    last_scan_location: "Local Carrier Facility",
    signature_required: false,
  };
}

export function executeEscalationTool(reason: string, brand?: string | null) {
  return {
    ticket_id: `ESC-${Math.floor(Date.now() % 1000000).toString().padStart(6, "0")}`,
    brand: brand || "Enterprise",
    queue: "Tier 2 Senior Resolution Specialist",
    priority: "High",
    estimated_wait_time: "3-5 minutes",
    status: "Assigned to Human Agent",
  };
}

export function createRAGEventStream(
  message: string,
  history: Array<{ role: string; content: string }>,
  brand?: string | null
): ReadableStream {
  const encoder = new TextEncoder();
  const startTime = Date.now();
  const userMessage = message.trim();
  const groqApiKey = process.env.GROQ_API_KEY || "";
  const groqModel = process.env.GROQ_MODEL || "llama-3.1-8b-instant";

  return new ReadableStream({
    async start(controller) {
      const sendEvent = (event: StreamEvent) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
      };

      // 1. Fast-Path Greeting
      if (isTrivialGreeting(userMessage)) {
        sendEvent({
          type: "thought",
          content: "Intent recognized as standard greeting. Executing direct fast-path response.",
        });

        const brandName = brand && brand !== "All Brands" ? brand : "Customer Support";
        const greetingText = `Hello! Welcome to **${brandName} Help & Support**. How can I assist you with your device, order, account, or billing today?`;
        const words = greetingText.split(" ");
        let tokenCount = 0;

        for (let i = 0; i < words.length; i++) {
          const chunk = words[i] + (i < words.length - 1 ? " " : "");
          tokenCount++;
          sendEvent({ type: "token", token: chunk });
          await new Promise((r) => setTimeout(r, 15));
        }

        const elapsed = Date.now() - startTime;
        sendEvent({
          type: "metrics",
          metrics: {
            latency_ms: elapsed,
            tokens_per_sec: Math.round((tokenCount / (elapsed / 1000 || 0.1))),
            sources_count: 0,
            fast_path: true,
            iterations: 0,
          },
        });
        sendEvent({ type: "done", done: true });
        controller.close();
        return;
      }

      // 2. Agentic ReAct Loop
      sendEvent({
        type: "thought",
        content: `Analyzing customer query for brand '${brand || "All"}' to retrieve grounded knowledge.`,
      });

      sendEvent({
        type: "tool_call",
        tool: "knowledge_base_search",
        input: { query: userMessage, brand },
      });

      const citations = searchKnowledgeBase(userMessage, brand, 4, 0.35);

      sendEvent({
        type: "tool_result",
        tool: "knowledge_base_search",
        output: { matches_found: citations.length, top_score: citations[0]?.score || 0.0 },
      });

      for (const cit of citations) {
        sendEvent({ type: "citation", citation: cit });
      }

      const toolObservations: string[] = [];
      if (citations.length > 0) {
        toolObservations.push(
          "Verified Knowledge Base Articles:\n" +
            citations
              .map((c) => `[${c.brand} | ${c.category}] Issue: ${c.query} -> Resolution: ${c.resolution}`)
              .join("\n")
        );
      }

      // Order check tool
      const orderMatch = userMessage.match(/\b(order|tracking|pkg|shipment|#)\s*([A-Za-z0-9\-_]{5,})\b/i);
      if (orderMatch) {
        const orderId = orderMatch[2];
        sendEvent({
          type: "thought",
          content: `Detected order tracking request for ID ${orderId}.`,
        });
        sendEvent({
          type: "tool_call",
          tool: "order_status_checker",
          input: { identifier: orderId },
        });
        const orderRes = executeOrderStatusTool(orderId);
        sendEvent({
          type: "tool_result",
          tool: "order_status_checker",
          output: orderRes,
        });
        toolObservations.push(`Order Logistics Status:\n${JSON.stringify(orderRes, null, 2)}`);
      }

      // Escalation tool
      const needsEscalation = /speak to human|real person|agent|fraud|unacceptable|lawsuit|manager/i.test(userMessage);
      if (needsEscalation) {
        sendEvent({
          type: "thought",
          content: "High urgency or escalation request detected. Triggering Tier-2 dispatch.",
        });
        sendEvent({
          type: "tool_call",
          tool: "escalate_to_human",
          input: { reason: userMessage.slice(0, 50), brand },
        });
        const escRes = executeEscalationTool(userMessage, brand);
        sendEvent({
          type: "tool_result",
          tool: "escalate_to_human",
          output: escRes,
        });
        toolObservations.push(`Escalation Queue:\n${JSON.stringify(escRes, null, 2)}`);
      }

      sendEvent({
        type: "thought",
        content: "Synthesizing grounded response from verified context.",
      });

      // 3. Generation (Groq Cloud API or High-Speed Mock Stream)
      let tokenCount = 0;

      if (groqApiKey) {
        try {
          const sysPrompt =
            "You are an enterprise customer support specialist. Answer the customer authoritatively, politely, and concisely using the provided verified Knowledge Base articles and tool observations.\n" +
            "Rules:\n1. Base your answer strictly on the verified knowledge base and tool outputs.\n2. Maintain a warm, professional brand tone.";

          const messages = [
            { role: "system", content: sysPrompt },
            ...history.slice(-4),
            {
              role: "user",
              content: `Customer Inquiry: ${userMessage}\n\nContext:\n${toolObservations.join("\n\n")}\n\nResponse:`,
            },
          ];

          const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${groqApiKey}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              model: groqModel,
              messages,
              stream: true,
              temperature: 0.2,
              max_tokens: 800,
            }),
          });

          if (res.ok && res.body) {
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buf = "";

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buf += decoder.decode(value, { stream: true });
              const lines = buf.split("\n");
              buf = lines.pop() || "";

              for (const line of lines) {
                if (line.startsWith("data: ")) {
                  const dataStr = line.slice(6).trim();
                  if (dataStr === "[DONE]") break;
                  try {
                    const parsed = JSON.parse(dataStr);
                    const delta = parsed.choices?.[0]?.delta?.content;
                    if (delta) {
                      tokenCount++;
                      sendEvent({ type: "token", token: delta });
                    }
                  } catch {}
                }
              }
            }
          } else {
            throw new Error(`Groq HTTP ${res.status}`);
          }
        } catch (err) {
          console.warn("Groq streaming fallback to mock:", err);
          // Fallback to simulated response
          tokenCount = await streamMockAnswer(sendEvent, citations, userMessage);
        }
      } else {
        tokenCount = await streamMockAnswer(sendEvent, citations, userMessage);
      }

      const elapsed = Date.now() - startTime;
      sendEvent({
        type: "metrics",
        metrics: {
          latency_ms: elapsed,
          tokens_per_sec: Math.round(tokenCount / (elapsed / 1000 || 0.1)),
          sources_count: citations.length,
          confidence_score: citations[0]?.score || 0.0,
          iterations: 1,
          backend: "Vercel Next.js Edge Engine",
        },
      });

      sendEvent({ type: "done", done: true });
      controller.close();
    },
  });
}

async function streamMockAnswer(
  sendEvent: (event: StreamEvent) => void,
  citations: KnowledgeCitation[],
  query: string
): Promise<number> {
  let text = "";

  if (citations.length > 0) {
    const top = citations[0];
    text =
      `Based on verified **${top.brand}** support procedures for *"${top.query}"*:\n\n` +
      `**Resolution Steps:**\n` +
      `${top.resolution}\n\n` +
      `If you have followed these steps and the issue is not resolved, please reply with your account email or order confirmation number and our team will escalate your ticket immediately.`;
  } else {
    text =
      `I have received your inquiry regarding: *"${query}"*.\n\n` +
      `To resolve this promptly:\n` +
      `1. Please verify your order number or registered account credentials.\n` +
      `2. For hardware or device issues, check your system settings or battery diagnostics.\n` +
      `3. For billing or subscription inquiries, you can request an instant review through your account dashboard.\n\n` +
      `Let me know if you would like me to dispatch this to a senior specialist!`;
  }

  const tokens = text.split(/(\s+)/);
  let count = 0;
  for (const t of tokens) {
    if (t) {
      count++;
      sendEvent({ type: "token", token: t });
      await new Promise((r) => setTimeout(r, 12));
    }
  }
  return count;
}
