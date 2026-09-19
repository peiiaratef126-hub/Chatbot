import { test, describe } from "node:test";
import assert from "node:assert";
import { cn, formatScore, formatLatency, formatTokensPerSec } from "../lib/utils.ts";

describe("Frontend Utils Test Suite", () => {
  test("cn: merges class names and resolves tailwind conflicts", () => {
    const result = cn("p-4", "text-red-500", "p-2");
    assert.strictEqual(result, "text-red-500 p-2");
  });

  test("cn: handles conditional classes cleanly", () => {
    const isActive = true;
    const isHidden = false;
    const result = cn("base-class", isActive && "active", isHidden && "hidden");
    assert.strictEqual(result, "base-class active");
  });

  test("formatScore: converts decimal score to percentage string", () => {
    assert.strictEqual(formatScore(0.854), "85.4%");
    assert.strictEqual(formatScore(1.0), "100.0%");
    assert.strictEqual(formatScore(0.0), "0.0%");
  });

  test("formatLatency: handles undefined, sub-second ms, and multi-second latencies", () => {
    assert.strictEqual(formatLatency(undefined), "--");
    assert.strictEqual(formatLatency(null as any), "--");
    assert.strictEqual(formatLatency(45), "45ms");
    assert.strictEqual(formatLatency(536.4), "536ms");
    assert.strictEqual(formatLatency(1500), "1.50s");
    assert.strictEqual(formatLatency(3250), "3.25s");
  });

  test("formatTokensPerSec: formats tokens per second with rounding", () => {
    assert.strictEqual(formatTokensPerSec(undefined), "--");
    assert.strictEqual(formatTokensPerSec(null as any), "--");
    assert.strictEqual(formatTokensPerSec(354.2), "354 t/s");
    assert.strictEqual(formatTokensPerSec(0), "0 t/s");
  });
});
