"use client";

import React from "react";
import Link from "next/link";
import { Bot, Sparkles, Layers, Github, ExternalLink, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { HealthData } from "@/lib/api";
import { ALL_BRANDS_FILTER as BRANDS } from "@/lib/constants";

interface HeaderProps {
  health: HealthData | null;
  selectedBrand: string;
  onSelectBrand: (brand: string) => void;
  onToggleContextDrawer: () => void;
  isDrawerOpen: boolean;
}

export function Header({
  health,
  selectedBrand,
  onSelectBrand,
  onToggleContextDrawer,
  isDrawerOpen,
}: HeaderProps) {
  const isMock = health?.mock_mode ?? true;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/40 bg-background/80 backdrop-blur-md px-4 lg:px-6 py-3 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand & Identity */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white shadow-lg shadow-emerald-500/20">
            <Bot className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold tracking-tight text-foreground">
                SupportRAG
              </h1>
              <Badge variant="brand" className="hidden sm:inline-flex text-[10px] py-0 px-2">
                Agentic v1.0
              </Badge>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {isMock ? (
                <span className="inline-flex items-center gap-1 text-amber-500 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  Zero-Cost Mock Mode
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-emerald-500 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Groq 300 t/s ({health?.groq_model || "llama-3.1-8b"})
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Center: Brand Selector Tabs (Desktop) */}
        <div className="hidden md:flex items-center gap-1 p-1 bg-muted/50 border border-border/60 rounded-2xl">
          {BRANDS.map((b) => {
            const active = selectedBrand === b;
            return (
              <button
                key={b}
                onClick={() => onSelectBrand(b)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                  active
                    ? "bg-background text-foreground shadow-sm font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {b}
              </button>
            );
          })}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          <Link
            href="/admin"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-input bg-background hover:bg-accent text-muted-foreground hover:text-foreground text-xs font-medium transition-colors"
            title="Escalations & Feedback Admin Dashboard"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
            <span className="hidden sm:inline">Admin</span>
          </Link>

          <Button
            variant="outline"
            size="sm"
            onClick={onToggleContextDrawer}
            className={`text-xs gap-1.5 rounded-xl ${
              isDrawerOpen ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400" : ""
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">KB Inspector</span>
          </Button>

          <a
            href="https://github.com/peiiaratef126-hub/Chatbot"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center h-9 w-9 rounded-xl border border-input text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title="peiiaratef126-hub/Chatbot on GitHub"
          >
            <Github className="w-4 h-4" />
          </a>

          <ThemeToggle />
        </div>
      </div>

      {/* Mobile Brand Selector Strip */}
      <div className="flex md:hidden items-center gap-1.5 overflow-x-auto pt-2.5 pb-1 no-scrollbar">
        {BRANDS.map((b) => {
          const active = selectedBrand === b;
          return (
            <button
              key={b}
              onClick={() => onSelectBrand(b)}
              className={`whitespace-nowrap px-3 py-1 rounded-full text-[11px] font-medium transition-all ${
                active
                  ? "bg-primary text-primary-foreground font-semibold"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {b}
            </button>
          );
        })}
      </div>
    </header>
  );
}
