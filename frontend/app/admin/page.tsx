"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  ArrowLeft,
  RotateCcw,
  AlertTriangle,
  ThumbsDown,
  Clock,
  Layers,
  CheckCircle2,
  ExternalLink,
  MessageSquare
} from "lucide-react";
import {
  fetchEscalations,
  fetchFeedback,
  EscalationItem,
  FeedbackItem,
  fetchHealth,
  HealthData
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";

export default function AdminDashboardPage() {
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"escalations" | "feedback">("escalations");

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [escData, fbData, healthData] = await Promise.all([
        fetchEscalations(50),
        fetchFeedback(false, 50),
        fetchHealth(),
      ]);
      setEscalations(escData);
      setFeedback(fbData);
      setHealth(healthData);
    } catch (e) {
      console.error("Failed loading admin dashboard data:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const negativeFeedback = feedback.filter((f) => f.rating === "down");
  const positiveFeedback = feedback.filter((f) => f.rating === "up");

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Admin Top Navigation */}
      <header className="sticky top-0 z-40 w-full border-b border-border/60 bg-background/80 backdrop-blur-md px-4 lg:px-8 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground p-1.5 rounded-xl hover:bg-muted transition-colors"
              title="Return to Customer Chat"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Back to Chat</span>
            </Link>

            <div className="h-4 w-[1px] bg-border" />

            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500">
                <ShieldAlert className="w-4 h-4" />
              </div>
              <h1 className="text-sm font-semibold tracking-tight">
                SupportRAG Admin & Oversight
              </h1>
              <Badge variant="outline" className="text-[10px] font-mono py-0 text-muted-foreground">
                Zero-Cost SQLite
              </Badge>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadData}
              disabled={isLoading}
              className="h-8 text-xs gap-1.5 rounded-xl"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content Dashboard */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 py-8 space-y-6">
        {/* Metric KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-sm space-y-1">
            <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
              <span>Total Escalations</span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-foreground">
              {escalations.length}
            </div>
            <p className="text-[11px] text-muted-foreground">Tier-2 supervisor requests</p>
          </div>

          <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-sm space-y-1">
            <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
              <span>Negative Feedback</span>
              <ThumbsDown className="w-4 h-4 text-rose-500" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-rose-500">
              {negativeFeedback.length}
            </div>
            <p className="text-[11px] text-muted-foreground">Downvoted assistant replies</p>
          </div>

          <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-sm space-y-1">
            <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
              <span>Positive Ratings</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-emerald-500">
              {positiveFeedback.length}
            </div>
            <p className="text-[11px] text-muted-foreground">Verified helpful resolutions</p>
          </div>

          <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-sm space-y-1">
            <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
              <span>Knowledge Base Index</span>
              <Layers className="w-4 h-4 text-teal-500" />
            </div>
            <div className="text-2xl font-bold tracking-tight text-foreground">
              {health?.indexed_documents_count ?? 100}
            </div>
            <p className="text-[11px] text-muted-foreground">
              Backend: {health?.vector_db_backend === "qdrant_cloud" ? "Qdrant Cloud" : "In-Memory KB"}
            </p>
          </div>
        </div>

        {/* Tab Selection Navigation */}
        <div className="flex items-center gap-2 border-b border-border/60 pb-3">
          <button
            onClick={() => setActiveTab("escalations")}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeTab === "escalations"
                ? "bg-primary text-primary-foreground shadow-sm font-semibold"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            Escalation Tickets ({escalations.length})
          </button>
          <button
            onClick={() => setActiveTab("feedback")}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              activeTab === "feedback"
                ? "bg-primary text-primary-foreground shadow-sm font-semibold"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            Customer Feedback Loop ({feedback.length})
          </button>
        </div>

        {/* Tab 1: Escalation Queue */}
        {activeTab === "escalations" && (
          <div className="space-y-3">
            {escalations.length === 0 ? (
              <div className="p-12 text-center rounded-2xl border border-border/60 bg-card">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-80" />
                <h3 className="text-sm font-semibold text-foreground">No Active Escalations</h3>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  No support conversations have required human intervention yet. Escalations triggered
                  by the ReAct agent will appear here automatically.
                </p>
              </div>
            ) : (
              <div className="rounded-2xl border border-border/60 bg-card overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-muted/50 border-b border-border/60 text-muted-foreground uppercase text-[10px] tracking-wider">
                      <tr>
                        <th className="px-4 py-3 font-semibold">Ticket ID</th>
                        <th className="px-4 py-3 font-semibold">Brand</th>
                        <th className="px-4 py-3 font-semibold">Language</th>
                        <th className="px-4 py-3 font-semibold">Customer Inquiry</th>
                        <th className="px-4 py-3 font-semibold">Reason</th>
                        <th className="px-4 py-3 font-semibold">Urgency</th>
                        <th className="px-4 py-3 font-semibold">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {escalations.map((esc) => (
                        <tr key={esc.ticket_id} className="hover:bg-muted/20 transition-colors">
                          <td className="px-4 py-3 font-mono font-semibold text-emerald-500 whitespace-nowrap">
                            {esc.ticket_id}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="px-2 py-0.5 rounded bg-muted font-medium text-[11px]">
                              {esc.brand}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <Badge
                              variant="outline"
                              className={`text-[10px] font-mono px-1.5 py-0 ${
                                esc.language === "ar"
                                  ? "border-emerald-500/40 text-emerald-500 bg-emerald-500/10"
                                  : "border-blue-500/40 text-blue-500 bg-blue-500/10"
                              }`}
                            >
                              {esc.language ? esc.language.toUpperCase() : "EN"}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 max-w-xs truncate text-foreground font-medium">
                            {esc.query}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground max-w-xs truncate">
                            {esc.reason}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <Badge variant="outline" className="text-[10px] border-amber-500/40 text-amber-500">
                              {esc.urgency || "High"}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground whitespace-nowrap font-mono text-[11px]">
                            {new Date(esc.created_at).toLocaleString([], {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Feedback Ratings */}
        {activeTab === "feedback" && (
          <div className="space-y-3">
            {feedback.length === 0 ? (
              <div className="p-12 text-center rounded-2xl border border-border/60 bg-card">
                <MessageSquare className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                <h3 className="text-sm font-semibold text-foreground">No Feedback Recorded Yet</h3>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  Customer ratings submitted via thumbs up / down buttons in chat will be collected here for DPO dataset extraction.
                </p>
              </div>
            ) : (
              <div className="rounded-2xl border border-border/60 bg-card overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-muted/50 border-b border-border/60 text-muted-foreground uppercase text-[10px] tracking-wider">
                      <tr>
                        <th className="px-4 py-3 font-semibold">Rating</th>
                        <th className="px-4 py-3 font-semibold">Session ID</th>
                        <th className="px-4 py-3 font-semibold">Feedback Comment / Reason</th>
                        <th className="px-4 py-3 font-semibold">Created At</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {feedback.map((f, idx) => (
                        <tr key={idx} className="hover:bg-muted/20 transition-colors">
                          <td className="px-4 py-3 whitespace-nowrap">
                            {f.rating === "up" ? (
                              <span className="inline-flex items-center gap-1 text-emerald-500 font-medium text-[11px]">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Positive
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-rose-500 font-medium text-[11px]">
                                <ThumbsDown className="w-3.5 h-3.5" /> Negative
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                            {f.session_id}
                          </td>
                          <td className="px-4 py-3 text-foreground">
                            {f.comment || <span className="text-muted-foreground italic">No comment provided</span>}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground whitespace-nowrap font-mono text-[11px]">
                            {new Date(f.created_at).toLocaleString([], {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
