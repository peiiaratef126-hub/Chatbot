"use client";

import React from "react";
import { Zap, Gauge, BookOpen, Database, Trash2, ShieldCheck } from "lucide-react";
import { PerformanceMetrics, HealthData } from "@/lib/api";
import { formatLatency, formatTokensPerSec } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface MetricsBarProps {
  metrics: PerformanceMetrics | null;
  health: HealthData | null;
  onClearChat: () => void;
  messageCount: number;
}

export function MetricsBar({
  metrics,
  health,
  onClearChat,
  messageCount,
}: MetricsBarProps) {
  const isConnected = health?.vector_db_connected;
  const backendLabel = health?.vector_db_backend === "qdrant_cloud"
    ? "Qdrant Cloud"
    : `In-Memory KB (${health?.indexed_documents_count || 100} docs)`;

  return (
    <div className="w-full border-b border-border/40 bg-muted/20 px-4 lg:px-6 py-2 text-xs text-muted-foreground transition-colors">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        {/* Left: Telemetry Badges */}
        <div className="flex flex-wrap items-center gap-3 sm:gap-5">
          <div className="flex items-center gap-1.5" title="Time to stream completion">
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            <span>Latency:</span>
            <span className="font-mono font-medium text-foreground">
              {formatLatency(metrics?.latency_ms)}
            </span>
          </div>

          <div className="flex items-center gap-1.5" title="Generation inference speed">
            <Gauge className="w-3.5 h-3.5 text-emerald-500" />
            <span>Speed:</span>
            <span className="font-mono font-medium text-foreground">
              {formatTokensPerSec(metrics?.tokens_per_sec)}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5" title="Grounded retrieved citations">
            <BookOpen className="w-3.5 h-3.5 text-sky-500" />
            <span>Grounding:</span>
            <span className="font-mono font-medium text-foreground">
              {metrics?.sources_count ?? 0} {metrics?.sources_count === 1 ? "source" : "sources"}
            </span>
          </div>

          <div className="hidden md:flex items-center gap-1.5" title="Vector DB Connection">
            <Database className="w-3.5 h-3.5 text-indigo-500" />
            <span>Index:</span>
            <span className="font-medium text-foreground">{backendLabel}</span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {messageCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearChat}
              className="h-7 px-2.5 text-[11px] text-muted-foreground hover:text-destructive gap-1 rounded-lg"
            >
              <Trash2 className="w-3 h-3" />
              <span>Reset Chat</span>
            </Button>
          )}

          <div className="flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Zero-Cost Architecture</span>
          </div>
        </div>
      </div>
    </div>
  );
}
