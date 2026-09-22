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
  Zap,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  Send,
  X
} from "lucide-react";
import { KnowledgeCitation, ToolTrace } from "@/lib/api";
import { formatScore, formatLatency } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AgentThoughtTrace } from "./agent-thought-trace";

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
  sessionId?: string | null;
  onFeedback?: (messageId: string, rating: "up" | "down", comment?: string) => void;
}

const FEEDBACK_TAGS = [
  "Hallucination",
  "Incorrect Language",
  "Incomplete",
  "Irrelevant info",
  "Incorrect advice",
  "Other"
];

export function MessageBubble({ message, isStreaming, sessionId, onFeedback }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [showContext, setShowContext] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState<"up" | "down" | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [selectedTag, setSelectedTag] = useState<string>("");
  const [customComment, setCustomComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleThumbsUp = () => {
    if (feedbackRating === "up") return;
    setFeedbackRating("up");
    setShowFeedbackModal(false);
    onFeedback?.(message.id, "up");
  };

  const handleThumbsDownClick = () => {
    if (feedbackRating === "down") {
      setShowFeedbackModal(!showFeedbackModal);
      return;
    }
    setFeedbackRating("down");
    setShowFeedbackModal(true);
  };

  const submitNegativeFeedback = () => {
    const finalComment = [selectedTag, customComment.trim()].filter(Boolean).join(": ");
    onFeedback?.(message.id, "down", finalComment || "Downvoted");
    setShowFeedbackModal(false);
    setFeedbackSubmitted(true);
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
          {/* Agent ReAct Thought & Tool Execution Trace */}
          {hasThoughts && (
            <AgentThoughtTrace
              thoughts={message.thoughts}
              tools={message.tools}
              isStreaming={isStreaming && !message.content}
            />
          )}

          {/* Main Bot Bubble */}
          <div className="relative group px-4 py-3.5 rounded-2xl rounded-tl-sm bg-card border border-border/60 shadow-sm text-sm leading-relaxed text-foreground">
            <div className="prose dark:prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:my-2">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content || (isStreaming ? "Thinking..." : "")}
              </ReactMarkdown>
            </div>

            {/* Bottom Info, Quality Feedback & Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-3 mt-3 border-t border-border/40 text-[11px] text-muted-foreground">
              <div className="flex flex-wrap items-center gap-2">
                <span>{message.timestamp}</span>
                {message.latencyMs && (
                  <span className="inline-flex items-center gap-1 font-mono text-amber-500 font-medium">
                    <Zap className="w-3 h-3" />
                    {formatLatency(message.latencyMs)}
                  </span>
                )}
                {feedbackSubmitted && (
                  <span className="text-emerald-500 text-[10px] font-medium flex items-center gap-1">
                    <Check className="w-2.5 h-2.5" /> Feedback saved
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
                    <span>{message.citations?.length} Verified Sources</span>
                    {showContext ? (
                      <ChevronUp className="w-3 h-3" />
                    ) : (
                      <ChevronDown className="w-3 h-3" />
                    )}
                  </button>
                )}

                {/* Thumbs Up Feedback */}
                {!isStreaming && (
                  <button
                    onClick={handleThumbsUp}
                    title="Helpful response"
                    className={`p-1 rounded-md transition-colors ${
                      feedbackRating === "up"
                        ? "text-emerald-500 bg-emerald-500/10"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50 opacity-60 group-hover:opacity-100"
                    }`}
                  >
                    <ThumbsUp className="w-3.5 h-3.5" />
                  </button>
                )}

                {/* Thumbs Down Feedback */}
                {!isStreaming && (
                  <button
                    onClick={handleThumbsDownClick}
                    title="Report issue or unhelpful response"
                    className={`p-1 rounded-md transition-colors ${
                      feedbackRating === "down"
                        ? "text-rose-500 bg-rose-500/10"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50 opacity-60 group-hover:opacity-100"
                    }`}
                  >
                    <ThumbsDown className="w-3.5 h-3.5" />
                  </button>
                )}

                {/* Copy Response Button */}
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

            {/* Negative Feedback Popover Modal */}
            {showFeedbackModal && (
              <div className="mt-3 p-3 rounded-xl border border-border/80 bg-background/95 shadow-md space-y-2.5 animate-fade-in">
                <div className="flex items-center justify-between text-xs font-semibold text-foreground">
                  <span>How can we improve this answer?</span>
                  <button
                    onClick={() => setShowFeedbackModal(false)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                
                {/* Feedback reason chips */}
                <div className="flex flex-wrap gap-1.5">
                  {FEEDBACK_TAGS.map((tag) => (
                    <button
                      key={tag}
                      onClick={() => setSelectedTag(tag === selectedTag ? "" : tag)}
                      className={`px-2 py-0.5 rounded-md text-[11px] font-medium border transition-colors ${
                        selectedTag === tag
                          ? "bg-rose-500/10 border-rose-500 text-rose-500"
                          : "border-border/60 text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>

                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Optional details (e.g., outdated steps)..."
                    value={customComment}
                    onChange={(e) => setCustomComment(e.target.value)}
                    className="flex-1 bg-muted/30 border border-border/60 rounded-md px-2 py-1 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-rose-500/50"
                  />
                  <Button
                    size="sm"
                    variant="default"
                    onClick={submitNegativeFeedback}
                    className="h-7 px-3 text-xs bg-rose-600 hover:bg-rose-500 text-white rounded-md"
                  >
                    Submit
                  </Button>
                </div>
              </div>
            )}

            {/* Collapsible Retrieved Context Inspector Body */}
            {hasCitations && showContext && (
              <div className="mt-3 pt-3 border-t border-border/40 space-y-2 animate-fade-in">
                <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
                  <span>Grounded Knowledge Base Context</span>
                  <span className="font-mono text-[10px] text-emerald-500">
                    FlashRank Reranked
                  </span>
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
                        <div className="flex items-center gap-1.5">
                          {c.reranked && (
                            <Badge variant="outline" className="text-[9px] py-0 border-emerald-500/40 text-emerald-500">
                              <Sparkles className="w-2.5 h-2.5 mr-0.5 inline" /> Reranked
                            </Badge>
                          )}
                          <Badge variant="success" className="text-[10px]">
                            {formatScore(c.score)} Match
                          </Badge>
                        </div>
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
