import { test, describe } from "node:test";
import assert from "node:assert";
import {
  fetchHealth,
  fetchSampleArticles,
  streamChatMessage,
  type ChatMessage,
  type HealthData,
  type KnowledgeCitation,
  type PerformanceMetrics,
} from "../lib/api.ts";

describe("Frontend API Client Test Suite", () => {
  test("fetchHealth: handles graceful fallback when server is offline", async () => {
    // Overriding fetch temporarily to simulate offline backend
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
      throw new Error("Network connection refused");
    };

    try {
      const health = await fetchHealth();
      assert.strictEqual(health, null, "Should return null on network failure");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test("fetchSampleArticles: handles fallback gracefully", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
      return new Response(JSON.stringify({ total: 0, sample_articles: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };

    try {
      const articles = await fetchSampleArticles();
      assert.ok(Array.isArray(articles));
      assert.strictEqual(articles.length, 0);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test("streamChatMessage: parses SSE event chunks correctly", async () => {
    const mockSSEPayload = [
      'data: {"type":"thought","content":"Testing thought"}\n\n',
      'data: {"type":"token","token":"Hello"}\n\n',
      'data: {"type":"token","token":" World"}\n\n',
      'data: {"type":"metrics","metrics":{"latency_ms":120,"tokens_per_sec":300,"sources_count":0}}\n\n',
      'data: {"type":"done","done":true}\n\n',
    ].join("");

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
      const encoder = new TextEncoder();
      const stream = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode(mockSSEPayload));
          controller.close();
        },
      });
      return new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      });
    };

    const thoughts: string[] = [];
    let accumulatedTokens = "";
    let capturedMetrics: PerformanceMetrics | null = null;
    let doneTriggered = false;

    try {
      await streamChatMessage(
        "Hi",
        [],
        "AppleSupport",
        {
          onThought: (t) => thoughts.push(t),
          onToken: (tok) => {
            accumulatedTokens += tok;
          },
          onMetrics: (m) => {
            capturedMetrics = m;
          },
          onDone: () => {
            doneTriggered = true;
          },
        }
      );

      assert.strictEqual(thoughts.length, 1);
      assert.strictEqual(thoughts[0], "Testing thought");
      assert.strictEqual(accumulatedTokens, "Hello World");
      assert.ok(capturedMetrics);
      assert.strictEqual((capturedMetrics as PerformanceMetrics).tokens_per_sec, 300);
      assert.strictEqual(doneTriggered, true);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
