"use client";

import React, { useState } from "react";
import {
  BrainCircuit,
  Wrench,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Database,
  PackageCheck,
  AlertTriangle,
  CheckCircle2,
  Clock
} from "lucide-react";
import { ToolTrace } from "@/lib/api";

interface AgentThoughtTraceProps {
  thoughts?: string[];
  tools?: ToolTrace[];
  isStreaming?: boolean;
}

export function AgentThoughtTrace({
  thoughts = [],
  tools = [],
  isStreaming = false
}: AgentThoughtTraceProps) {
  const [isOpen, setIsOpen] = useState<boolean>(true);
  const totalEvents = thoughts.length + tools.length;

  if (totalEvents === 0 && !isStreaming) {
    return null;
  }

  const getToolBadgeInfo = (toolName: string) => {
    switch (toolName.toLowerCase()) {
      case "knowledge_base_search":
        return {
          label: "Vector Search",
          icon: Database,
          bgClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
          iconClass: "text-emerald-400"
        };
      case "check_order_status":
      case "order_status_checker":
        return {
          label: "Logistics ERP",
          icon: PackageCheck,
          bgClass: "bg-sky-500/10 text-sky-400 border-sky-500/20",
          iconClass: "text-sky-400"
        };
      case "escalate_to_human":
        return {
          label: "Human Dispatch",
          icon: AlertTriangle,
          bgClass: "bg-amber-500/10 text-amber-400 border-amber-500/20",
          iconClass: "text-amber-400"
        };
      default:
        return {
          label: toolName,
          icon: Wrench,
          bgClass: "bg-purple-500/10 text-purple-400 border-purple-500/20",
          iconClass: "text-purple-400"
        };
    }
  };

  return (
    <div className="w-full rounded-xl border border-border/60 bg-surface/80 dark:bg-[#0e0e11] backdrop-blur-md overflow-hidden transition-all shadow-sm mb-3">
      {/* Header Bar */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 bg-muted/20 hover:bg-muted/30 transition-colors text-left font-mono text-[11px] select-none"
      >
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center">
            {isStreaming ? (
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
            ) : (
              <BrainCircuit className="w-3.5 h-3.5 text-emerald-500" />
            )}
          </div>

          <span className="font-semibold tracking-wide text-foreground/90">
            Agent ReAct Reasoning Trace
          </span>

          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-500 dark:text-emerald-400 border border-emerald-500/20">
            {tools.length} {tools.length === 1 ? "tool" : "tools"} executed
          </span>

          {isStreaming && (
            <span className="hidden sm:inline-flex items-center gap-1 text-[10px] text-muted-foreground animate-pulse font-sans">
              <Sparkles className="w-3 h-3 text-amber-400" />
              <span>Analyzing intent & retrieving grounded evidence...</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-muted-foreground">
          {isOpen ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </div>
      </button>

      {/* Collapsible Timeline Content */}
      {isOpen && (
        <div className="p-3.5 border-t border-border/40 font-mono text-[11px] space-y-3 bg-background/40">
          {/* Thoughts List */}
          {thoughts.map((thought, idx) => (
            <div
              key={`th-${idx}`}
              className="flex items-start gap-2.5 text-muted-foreground group"
            >
              <div className="mt-1 flex items-center justify-center w-4 h-4 rounded-full bg-emerald-500/10 text-emerald-500 shrink-0 text-[9px] font-bold">
                T{idx + 1}
              </div>
              <div className="flex-1 text-xs leading-relaxed text-zinc-700 dark:text-zinc-300">
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold mr-1.5">
                  Thought:
                </span>
                {thought}
              </div>
            </div>
          ))}

          {/* Tools List */}
          {tools.map((tool, idx) => {
            const badge = getToolBadgeInfo(tool.tool);
            const Icon = badge.icon;
            return (
              <div
                key={`tool-${idx}`}
                className="rounded-lg border border-border/50 bg-card/60 p-3 space-y-2 relative overflow-hidden"
              >
                {/* Tool Status Pill */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border font-semibold text-[11px] ${badge.bgClass}`}
                    >
                      <Icon className={`w-3 h-3 ${badge.iconClass}`} />
                      <span>{badge.label}</span>
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      `{tool.tool}`
                    </span>
                  </div>

                  <span className="inline-flex items-center gap-1 text-[10px] text-emerald-500 font-medium font-sans">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>Completed</span>
                  </span>
                </div>

                {/* Input Payload */}
                {tool.input && Object.keys(tool.input).length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground/80 tracking-wider">
                      Arguments:
                    </span>
                    <div className="p-2 rounded bg-muted/40 border border-border/30 text-[10px] text-zinc-700 dark:text-zinc-300 overflow-x-auto">
                      <pre className="font-mono">
                        {JSON.stringify(tool.input, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Output Payload */}
                {tool.output && Object.keys(tool.output).length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground/80 tracking-wider">
                      Observation Result:
                    </span>
                    <div className="p-2 rounded bg-muted/40 border border-border/30 text-[10px] text-zinc-700 dark:text-zinc-300 overflow-x-auto max-h-36">
                      <pre className="font-mono whitespace-pre-wrap">
                        {JSON.stringify(tool.output, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Active Streaming Thinking Indicator */}
          {isStreaming && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground py-1 font-sans">
              <Clock className="w-3.5 h-3.5 text-amber-500 animate-spin" />
              <span>Synthesizing final grounded resolution...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
