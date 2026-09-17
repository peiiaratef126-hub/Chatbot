"use client";

import React, { useRef, useEffect } from "react";
import { Bot, Sparkles } from "lucide-react";
import { MessageBubble, ChatMessageItem } from "./message-bubble";
import { SuggestedPrompts } from "./suggested-prompts";

interface MessageListProps {
  messages: ChatMessageItem[];
  isStreaming: boolean;
  onSelectPrompt: (prompt: string, brand?: string) => void;
  selectedBrand: string;
}

export function MessageList({
  messages,
  isStreaming,
  onSelectPrompt,
  selectedBrand,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-2xl mx-auto w-full">
        <div className="w-14 h-14 rounded-3xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white flex items-center justify-center shadow-xl shadow-emerald-500/20 mb-4 animate-bounce">
          <Bot className="w-7 h-7" />
        </div>

        <h2 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl mb-2">
          Enterprise Customer Support Agent
        </h2>
        <p className="text-sm text-muted-foreground leading-relaxed max-w-md mb-6">
          Zero-cost, portfolio-grade RAG architecture grounded in 100+ verified
          support workflows. Ask questions or select an inquiry below:
        </p>

        <div className="w-full">
          <SuggestedPrompts
            onSelectPrompt={onSelectPrompt}
            selectedBrand={selectedBrand}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 lg:px-8 py-6 space-y-6"
    >
      <div className="max-w-4xl mx-auto space-y-6">
        {messages.map((msg, idx) => (
          <MessageBubble
            key={msg.id || idx}
            message={msg}
            isStreaming={isStreaming && idx === messages.length - 1 && msg.role === "assistant"}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
