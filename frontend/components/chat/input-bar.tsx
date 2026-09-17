"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Square, Sparkles, CornerDownLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

interface InputBarProps {
  onSendMessage: (message: string) => void;
  onStopStreaming?: () => void;
  isStreaming: boolean;
  selectedBrand: string;
}

export function InputBar({
  onSendMessage,
  onStopStreaming,
  isStreaming,
  selectedBrand,
}: InputBarProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isStreaming) {
      textareaRef.current?.focus();
    }
  }, [isStreaming]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (isStreaming) {
      onStopStreaming?.();
      return;
    }
    const trimmed = input.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        180
      )}px`;
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 lg:px-8 pb-4 pt-2">
      <div className="relative flex flex-col rounded-2xl border border-border/80 bg-card shadow-lg focus-within:border-emerald-500/60 focus-within:ring-2 focus-within:ring-emerald-500/10 transition-all">
        {/* Input Area */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={`Ask about ${selectedBrand === "All Brands" ? "any product, tracking, or order" : selectedBrand}...`}
          rows={1}
          className="w-full resize-none bg-transparent px-4 pt-3.5 pb-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none max-h-44"
        />

        {/* Action Controls Toolbar */}
        <div className="flex items-center justify-between px-3 py-2 border-t border-border/30 bg-muted/10">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="hidden sm:inline-flex items-center gap-1 font-mono">
              <CornerDownLeft className="w-3 h-3 text-muted-foreground/80" />
              Enter to send
            </span>
            <span className="hidden sm:inline-block text-border">•</span>
            <span className="hidden sm:inline font-mono">Shift + Enter for newline</span>
          </div>

          <div className="flex items-center gap-2">
            {isStreaming ? (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={onStopStreaming}
                className="h-8 px-3 rounded-xl text-xs gap-1.5 font-medium"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Stop</span>
              </Button>
            ) : (
              <Button
                type="button"
                variant="default"
                size="sm"
                onClick={handleSubmit}
                disabled={!input.trim()}
                className="h-8 px-3 rounded-xl text-xs gap-1.5 font-medium bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                <span>Send</span>
                <Send className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
