import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

export function formatLatency(ms?: number): string {
  if (ms === undefined || ms === null) return "--";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatTokensPerSec(tps?: number): string {
  if (tps === undefined || tps === null) return "--";
  return `${Math.round(tps)} t/s`;
}
