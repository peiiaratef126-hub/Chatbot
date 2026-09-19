import { test, describe } from "node:test";
import assert from "node:assert";
import {
  isTrivialGreeting,
  searchKnowledgeBase,
  executeOrderStatusTool,
  executeEscalationTool,
  createRAGEventStream,
  type StreamEvent,
} from "../lib/rag-engine.ts";

describe("Frontend RAG Engine Test Suite", () => {
  describe("isTrivialGreeting", () => {
    test("identifies single-word greetings", () => {
      assert.strictEqual(isTrivialGreeting("hi"), true);
      assert.strictEqual(isTrivialGreeting("hello"), true);
      assert.strictEqual(isTrivialGreeting("Hey"), true);
      assert.strictEqual(isTrivialGreeting("HOWDY"), true);
      assert.strictEqual(isTrivialGreeting("yo"), true);
    });

    test("identifies greetings with punctuation and whitespace", () => {
      assert.strictEqual(isTrivialGreeting("  Hello!  "), true);
      assert.strictEqual(isTrivialGreeting("Hi there."), true);
      assert.strictEqual(isTrivialGreeting("Good morning!"), true);
      assert.strictEqual(isTrivialGreeting("good evening"), true);
    });

    test("identifies ultra-short messages as trivial", () => {
      assert.strictEqual(isTrivialGreeting("h"), true);
      assert.strictEqual(isTrivialGreeting("hi"), true);
    });

    test("rejects domain queries and actionable inquiries", () => {
      assert.strictEqual(isTrivialGreeting("Where is my package #ORD-9821?"), false);
      assert.strictEqual(isTrivialGreeting("My iPhone battery drains rapidly after update"), false);
      assert.strictEqual(isTrivialGreeting("How do I cancel my subscription?"), false);
      assert.strictEqual(isTrivialGreeting("I need to speak with a human agent"), false);
    });
  });

  describe("searchKnowledgeBase", () => {
    test("retrieves relevant articles for brand-specific query", () => {
      const results = searchKnowledgeBase("battery drains rapidly", "AppleSupport", 3, 0.2);
      assert.ok(results.length > 0, "Should return at least one result");
      assert.strictEqual(results[0].brand, "AppleSupport");
      assert.ok(results[0].query.toLowerCase().includes("battery"));
      assert.ok(results[0].score > 0);
    });

    test("filters by brand correctly", () => {
      const appleResults = searchKnowledgeBase("battery", "AppleSupport", 5, 0.1);
      for (const res of appleResults) {
        assert.strictEqual(res.brand, "AppleSupport");
      }

      const amazonResults = searchKnowledgeBase("package delivery", "AmazonHelp", 5, 0.1);
      for (const res of amazonResults) {
        assert.strictEqual(res.brand, "AmazonHelp");
      }
    });

    test("respects topK parameter", () => {
      const results = searchKnowledgeBase("support", "All Brands", 2, 0.05);
      assert.ok(results.length <= 2, `Expected at most 2 results, got ${results.length}`);
    });

    test("returns empty array for nonsensical query with high threshold", () => {
      const results = searchKnowledgeBase("xyzabc999nonexistentquery", "All Brands", 4, 0.8);
      assert.strictEqual(results.length, 0);
    });
  });

  describe("executeOrderStatusTool", () => {
    test("normalizes order identifier and returns ERP payload", () => {
      const order = executeOrderStatusTool("ord-882194");
      assert.strictEqual(order.order_id, "ORD-882194");
      assert.strictEqual(order.status, "In Transit - Out for Delivery");
      assert.strictEqual(order.carrier, "UPS Expedited");
      assert.strictEqual(typeof order.estimated_delivery, "string");
      assert.strictEqual(order.signature_required, false);
    });
  });

  describe("executeEscalationTool", () => {
    test("generates ticket with standard prefix and priority", () => {
      const esc = executeEscalationTool("Product damaged on arrival", "AmazonHelp");
      assert.ok(esc.ticket_id.startsWith("ESC-"), "Ticket ID should start with ESC-");
      assert.strictEqual(esc.brand, "AmazonHelp");
      assert.strictEqual(esc.queue, "Tier 2 Senior Resolution Specialist");
      assert.strictEqual(esc.priority, "High");
      assert.strictEqual(esc.status, "Assigned to Human Agent");
    });

    test("defaults brand to Enterprise when omitted", () => {
      const esc = executeEscalationTool("Urgent issue", null);
      assert.strictEqual(esc.brand, "Enterprise");
    });
  });

  describe("createRAGEventStream", () => {
    async function collectStreamEvents(stream: ReadableStream): Promise<StreamEvent[]> {
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      const events: StreamEvent[] = [];
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6).trim();
            if (jsonStr) {
              events.push(JSON.parse(jsonStr));
            }
          }
        }
      }
      return events;
    }

    test("streams fast-path greeting events with sub-millisecond metrics", async () => {
      const stream = createRAGEventStream("Hello!", [], "AppleSupport");
      const events = await collectStreamEvents(stream);

      assert.ok(events.length >= 4, "Should emit multiple SSE events");
      assert.strictEqual(events[0].type, "thought");
      assert.ok(events[0].content?.includes("fast-path"));

      const tokenEvents = events.filter((e) => e.type === "token");
      assert.ok(tokenEvents.length > 0, "Should emit greeting tokens");

      const metricsEvent = events.find((e) => e.type === "metrics");
      assert.ok(metricsEvent, "Should emit metrics event");
      assert.strictEqual(metricsEvent.metrics?.fast_path, true);

      const doneEvent = events.find((e) => e.type === "done");
      assert.ok(doneEvent?.done, "Should emit done event");
    });

    test("executes order tracking tool when tracking number is present", async () => {
      const stream = createRAGEventStream(
        "Where is my package #ORDER-12345?",
        [],
        "AmazonHelp"
      );
      const events = await collectStreamEvents(stream);

      const toolCall = events.find(
        (e) => e.type === "tool_call" && e.tool === "order_status_checker"
      );
      assert.ok(toolCall, "Should trigger order_status_checker tool");
      assert.strictEqual(toolCall.input?.identifier, "ORDER-12345");

      const toolResult = events.find(
        (e) => e.type === "tool_result" && e.tool === "order_status_checker"
      );
      assert.ok(toolResult, "Should emit tool_result for order_status_checker");
      assert.strictEqual(toolResult.output?.order_id, "ORDER-12345");
    });

    test("executes human escalation tool when high urgency is detected", async () => {
      const stream = createRAGEventStream(
        "I demand to speak to a real person immediately!",
        [],
        "Uber_Support"
      );
      const events = await collectStreamEvents(stream);

      const toolCall = events.find(
        (e) => e.type === "tool_call" && e.tool === "escalate_to_human"
      );
      assert.ok(toolCall, "Should trigger escalate_to_human tool");

      const toolResult = events.find(
        (e) => e.type === "tool_result" && e.tool === "escalate_to_human"
      );
      assert.ok(toolResult, "Should emit tool_result for escalate_to_human");
      assert.ok(toolResult.output?.ticket_id.startsWith("ESC-"));
    });
  });
});
