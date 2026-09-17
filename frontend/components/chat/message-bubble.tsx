"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Bot,
  User,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Wrench,
  BrainCircuit,
  Zap,
} from "lucide-react";
import { KnowledgeCitation, ToolTrace } from "@/lib/api";
import { formatScore, formatLatency } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface ChatMessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: KnowledgeCitation[];
  thoughts?: string[];
  tools?: ToolTrace[];
  latencyMs?: number;
  timestamp: string;
}

interface MessageBubbleProps {
  message: ChatMessageItem;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [showContext, setShowContext] = useState(false);
  const [showThoughts, setShowThoughts] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end w-full animate-fade-in">
        <div className="max-w-[85%] sm:max-w-[75%] flex items-end gap-2">
          <div className="flex flex-col items-end">
            <div className="px-4 py-3 rounded-2xl rounded-tr-sm bg-emerald-600 text-white shadow-sm text-sm leading-relaxed">
              {message.content}
            </div>
            <span className="text-[10px] text-muted-foreground mt-1 mr-1">
              {message.timestamp}
            </span>
          </div>
          <div className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center text-muted-foreground shrink-0 mb-4">
            <User className="w-4 h-4" />
          </div>
        </div>
      </div>
    );
  }

  const hasCitations = message.citations && message.citations.length > 0;
  const hasThoughts =
    (message.thoughts && message.thoughts.length > 0) ||
    (message.tools && message.tools.length > 0);

  return (
    <div className="flex justify-start w-full animate-fade-in">
      <div className="max-w-[92%] sm:max-w-[85%] flex items-start gap-3">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
          <Bot className="w-4 h-4" />
        </div>

        <div className="flex-1 space-y-2">
          {/* Agent Thoughts / Tool Calls Accordion */}
          {hasThoughts && (
            <div className="rounded-xl border border-border/50 bg-muted/30 overflow-hidden text-xs">
              <button
                onClick={() => setShowThoughts(!showThoughts)}
                className="w-full flex items-center justify-between px-3 py-2 text-muted-foreground hover:text-foreground transition-colors font-mono text-[11px]"
              >
                <div className="flex items-center gap-1.5">
                  <BrainCircuit className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Agent ReAct Trace ({message.tools?.length || 0} tools executed)</span>
                </div>
                {showThoughts ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>

              {showThoughts && (
                <div className="p-3 border-t border-border/40 space-y-2 font-mono text-[11px] bg-background/50">
                  {message.thoughts?.map((th, i) => (
                    <div key={i} className="text-muted-foreground flex items-start gap-1.5">
                      <span className="text-emerald-500">▶</span>
                      <span>{th}</span>
                    </div>
                  ))}

                  {message.tools?.map((tool, i) => (
                    <div
                      key={i}
                      className="p-2 rounded-lg bg-muted/60 border border-border/40 space-y-1"
                    >
                      <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                        <Wrench className="w-3 h-3" />
                        <span>Tool: {tool.tool}</span>
                      </div>
                      {tool.input && (
                        <div className="text-[10px] text-muted-foreground">
                          Input: {JSON.stringify(tool.input)}
                        </div>
                      )}
                      {tool.output && (
                        <div className="text-[10px] text-muted-foreground">
                          Output: {JSON.stringify(tool.output)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Main Bot Bubble */}
          <div className="relative group px-4 py-3.5 rounded-2xl rounded-tl-sm bg-card border border-border/60 shadow-sm text-sm leading-relaxed text-foreground">
            <div className="prose dark:prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:my-2">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content || (isStreaming ? "Thinking..." : "")}
              </ReactMarkdown>
            </div>

            {/* Bottom Info & Copy Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-3 mt-3 border-t border-border/40 text-[11px] text-muted-foreground">
              <div className="flex flex-wrap items-center gap-2">
                <span>{message.timestamp}</span>
                {message.latencyMs && (
                  <span className="inline-flex items-center gap-1 font-mono text-amber-500 font-medium">
                    <Zap className="w-3 h-3" />
                    {formatLatency(message.latencyMs)}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                {/* Collapsible Retrieved Context Button */}
                {hasCitations && (
                  <button
                    onClick={() => setShowContext(!showContext)}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 transition-colors font-medium text-[11px]"
                  >
                    <BookOpen className="w-3 h-3" />
                    <span>
                      {message.citations?.length} Verified Sources
                    </span>
                    {showContext ? (
                      <ChevronUp className="w-3 h-3" />
                    ) : (
                      <ChevronDown className="w-3 h-3" />
                    )}
                  </button>
                )}

                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCopy}
                  className="h-6 w-6 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Copy response"
                >
                  {copied ? (
                    <Check className="w-3 h-3 text-emerald-500" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </Button>
              </div>
            </div>

            {/* Collapsible Retrieved Context Inspector Body */}
            {hasCitations && showContext && (
              <div className="mt-3 pt-3 border-t border-border/40 space-y-2 animate-fade-in">
                <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <span>Grounded Knowledge Base Context</span>
                </div>
                <div className="grid grid-cols-1 gap-2">
                  {message.citations?.map((c) => (
                    <div
                      key={c.doc_id}
                      className="p-3 rounded-xl border border-border/60 bg-muted/40 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                          {c.brand}
                        </span>
                        <Badge variant="success" className="text-[10px]">
                          {formatScore(c.score)} Match
                        </Badge>
                      </div>
                      <div className="font-medium text-foreground text-xs">
                        Problem: {c.query}
                      </div>
                      <div className="text-muted-foreground text-xs leading-relaxed">
                        Resolution: {c.resolution}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
