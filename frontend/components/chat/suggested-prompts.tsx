"use client";

import React from "react";
import { Sparkles, ArrowUpRight } from "lucide-react";

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string, brand?: string) => void;
  selectedBrand: string;
}

interface PromptItem {
  text: string;
  brand: string;
  category: string;
}

const ALL_PROMPTS: PromptItem[] = [
  {
    text: "My iPhone battery drops from 50% to 10% in 15 minutes. What should I do?",
    brand: "AppleSupport",
    category: "Technical Support",
  },
  {
    text: "Package marked delivered but not received. Tracking #ORDER-882194",
    brand: "AmazonHelp",
    category: "Orders & Delivery",
  },
  {
    text: "I was charged an unexpected cleaning fee after my ride. How can I dispute it?",
    brand: "Uber_Support",
    category: "Billing & Payments",
  },
  {
    text: "Music stops playing whenever my phone screen locks or turns off",
    brand: "SpotifyCares",
    category: "Technical Support",
  },
  {
    text: "My flight was delayed overnight and checked baggage is missing",
    brand: "Delta",
    category: "Reservations & Travel",
  },
  {
    text: "Can I exchange worn running shoes within the 60-day trial period?",
    brand: "NikeSupport",
    category: "Orders & Delivery",
  },
  {
    text: "I want to speak with a human agent about unauthorized account billing",
    brand: "All Brands",
    category: "Human Escalation",
  },
];

export function SuggestedPrompts({
  onSelectPrompt,
  selectedBrand,
}: SuggestedPromptsProps) {
  const filtered =
    selectedBrand === "All Brands"
      ? ALL_PROMPTS
      : ALL_PROMPTS.filter((p) => p.brand === selectedBrand || p.brand === "All Brands");

  return (
    <div className="w-full py-4">
      <div className="flex items-center gap-1.5 mb-3 text-xs font-medium text-muted-foreground">
        <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
        <span>Suggested verified inquiries for {selectedBrand}:</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {filtered.slice(0, 6).map((item, idx) => (
          <button
            key={idx}
            onClick={() => onSelectPrompt(item.text, item.brand)}
            className="group relative flex flex-col justify-between p-3.5 text-left rounded-2xl border border-border/60 bg-card/50 hover:bg-card hover:border-emerald-500/40 hover:shadow-md transition-all text-xs duration-150"
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <span className="font-mono text-[10px] px-2 py-0.5 rounded-md bg-muted text-muted-foreground font-medium">
                {item.brand}
              </span>
              <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 group-hover:text-emerald-500 transition-all transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </div>
            <p className="text-foreground/90 font-medium line-clamp-2 leading-relaxed">
              "{item.text}"
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
