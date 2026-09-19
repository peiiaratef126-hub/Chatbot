"use client";

import React, { useState, useEffect, useRef } from "react";
import { Header } from "@/components/layout/header";
import { MetricsBar } from "@/components/layout/metrics-bar";
import { MessageList } from "./message-list";
import { InputBar } from "./input-bar";
import { ContextDrawer } from "./context-drawer";
import { ChatMessageItem } from "./message-bubble";
import {
  fetchHealth,
  streamChatMessage,
  HealthData,
  PerformanceMetrics,
  KnowledgeCitation,
  ToolTrace,
} from "@/lib/api";

export function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedBrand, setSelectedBrand] = useState("All Brands");
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchHealth().then((h) => {
      if (h) setHealth(h);
    });
  }, []);

  const handleSendMessage = async (text: string, overrideBrand?: string) => {
    if (isStreaming) return;

    const brandToUse = overrideBrand || selectedBrand;
    const now = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMessageItem: ChatMessageItem = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: now,
    };

    const assistantMessageId = `assistant-${Date.now()}`;
    const initialAssistantItem: ChatMessageItem = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      citations: [],
      thoughts: [],
      tools: [],
      timestamp: now,
    };

    const updatedMessages = [...messages, userMessageItem, initialAssistantItem];
    setMessages(updatedMessages);
    setIsStreaming(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let streamedContent = "";
    const collectedCitations: KnowledgeCitation[] = [];
    const collectedThoughts: string[] = [];
    const collectedTools: ToolTrace[] = [];

    // Frame-rate throttle (60fps) to eliminate React rendering stutter at 350+ tok/sec
    let renderRafId: any = null;
    let pendingContent = "";

    const scheduleContentFlush = () => {
      if (renderRafId === null) {
        if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
          renderRafId = window.requestAnimationFrame(() => {
            renderRafId = null;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: pendingContent }
                  : msg
              )
            );
          });
        } else {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: pendingContent }
                : msg
            )
          );
        }
      }
    };

    const flushContentImmediately = () => {
      if (renderRafId !== null) {
        if (typeof window !== "undefined" && typeof window.cancelAnimationFrame === "function") {
          window.cancelAnimationFrame(renderRafId);
        }
        renderRafId = null;
      }
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: pendingContent }
            : msg
        )
      );
    };

    try {
      await streamChatMessage(
        text,
        messages.map((m) => ({ role: m.role, content: m.content })),
        brandToUse,
        {
          onThought: (content) => {
            collectedThoughts.push(content);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, thoughts: [...collectedThoughts] }
                  : msg
              )
            );
          },
          onToolCall: (tool, input) => {
            collectedTools.push({ tool, input });
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, tools: [...collectedTools] }
                  : msg
              )
            );
          },
          onToolResult: (tool, output) => {
            const last = collectedTools.find((t) => t.tool === tool);
            if (last) last.output = output;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, tools: [...collectedTools] }
                  : msg
              )
            );
          },
          onCitation: (cit) => {
            collectedCitations.push(cit);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, citations: [...collectedCitations] }
                  : msg
              )
            );
          },
          onToken: (token) => {
            pendingContent += token;
            scheduleContentFlush();
          },
          onMetrics: (m) => {
            setMetrics(m);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, latencyMs: m.latency_ms }
                  : msg
              )
            );
          },
          onError: (err) => {
            flushContentImmediately();
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      content:
                        msg.content + `\n\n*(Error encountered: ${err})*`,
                    }
                  : msg
              )
            );
          },
          onDone: () => {
            flushContentImmediately();
            setIsStreaming(false);
          },
        },
        controller.signal
      );
    } catch (err: any) {
      flushContentImmediately();
      if (err.name !== "AbortError") {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content:
                    msg.content ||
                    "*(Notice: Could not connect to backend service. Please check that the backend is running on port 7860.)*",
                }
              : msg
          )
        );
      }
    } finally {
      flushContentImmediately();
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
    }
  };

  const handleClearChat = () => {
    handleStopStreaming();
    setMessages([]);
    setMetrics(null);
  };

  return (
    <div className="flex flex-col h-[100dvh] w-full overflow-hidden bg-background">
      {/* Header */}
      <Header
        health={health}
        selectedBrand={selectedBrand}
        onSelectBrand={setSelectedBrand}
        onToggleContextDrawer={() => setIsDrawerOpen(!isDrawerOpen)}
        isDrawerOpen={isDrawerOpen}
      />

      {/* Metrics Bar */}
      <MetricsBar
        metrics={metrics}
        health={health}
        onClearChat={handleClearChat}
        messageCount={messages.length}
      />

      {/* Center Chat Message Stream */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <MessageList
          messages={messages}
          isStreaming={isStreaming}
          onSelectPrompt={(p, b) => handleSendMessage(p, b)}
          selectedBrand={selectedBrand}
        />

        {/* Input Bar */}
        <InputBar
          onSendMessage={(msg) => handleSendMessage(msg)}
          onStopStreaming={handleStopStreaming}
          isStreaming={isStreaming}
          selectedBrand={selectedBrand}
        />
      </main>

      {/* Slide-over Knowledge Base Inspector */}
      <ContextDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        activeBrand={selectedBrand}
      />
    </div>
  );
}
