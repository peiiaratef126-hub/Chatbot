"use client";

import React, { useState, useEffect } from "react";
import { X, Database, Search, ShieldCheck, Cpu, ExternalLink } from "lucide-react";
import { KnowledgeCitation, fetchSampleArticles } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ContextDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeBrand: string;
}

export function ContextDrawer({
  isOpen,
  onClose,
  activeBrand,
}: ContextDrawerProps) {
  const [articles, setArticles] = useState<KnowledgeCitation[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && articles.length === 0) {
      setLoading(true);
      fetchSampleArticles()
        .then((docs) => setArticles(docs))
        .finally(() => setLoading(false));
    }
  }, [isOpen, articles.length]);

  if (!isOpen) return null;

  const filteredArticles = articles.filter((a) => {
    const matchesBrand =
      activeBrand === "All Brands" || a.brand.toLowerCase() === activeBrand.toLowerCase();
    const matchesQuery =
      searchQuery === "" ||
      a.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.resolution.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesBrand && matchesQuery;
  });

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm transition-opacity">
      <div className="w-full max-w-md h-full bg-background border-l border-border/60 shadow-2xl flex flex-col animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border/40">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-500" />
            <h2 className="text-sm font-semibold tracking-tight">
              Knowledge Base Inspector
            </h2>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 rounded-lg"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Search & Brand Banner */}
        <div className="p-4 border-b border-border/40 space-y-3 bg-muted/20">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search verified support solutions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-background rounded-xl border border-input text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              Showing {filteredArticles.length} of {articles.length || 100} indexed articles
            </span>
            <Badge variant="brand">{activeBrand}</Badge>
          </div>
        </div>

        {/* List of Articles */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-24 rounded-xl bg-muted/40 animate-pulse"
                />
              ))}
            </div>
          ) : filteredArticles.length === 0 ? (
            <div className="text-center py-12 text-xs text-muted-foreground">
              No matching knowledge articles found.
            </div>
          ) : (
            filteredArticles.map((art) => (
              <div
                key={art.doc_id}
                className="p-3.5 rounded-xl border border-border/60 bg-card/60 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                    {art.brand}
                  </span>
                  <span className="text-[10px] text-muted-foreground font-medium">
                    {art.category}
                  </span>
                </div>

                <div className="font-medium text-foreground">
                  {art.query}
                </div>

                <div className="text-muted-foreground leading-relaxed">
                  {art.resolution}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer Info */}
        <div className="p-4 border-t border-border/40 bg-muted/30 text-[11px] text-muted-foreground space-y-1.5">
          <div className="flex items-center gap-1.5 font-medium text-foreground">
            <Cpu className="w-3.5 h-3.5 text-sky-500" />
            <span>Qdrant Cosine Distance Indexing</span>
          </div>
          <p>
            Embeddings generated with BAAI/bge-small-en-v1.5 (384 dimensions).
            Threshold score &gt;= 0.60 required for citation grounding.
          </p>
        </div>
      </div>
    </div>
  );
}
