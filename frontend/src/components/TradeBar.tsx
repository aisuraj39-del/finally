"use client";

import { useState, type FormEvent } from "react";

import { fmtPrice, fmtQty } from "@/lib/format";
import type { Side } from "@/lib/types";

interface Props {
  ticker: string;
  onTickerChange: (ticker: string) => void;
  price: number | null;
  onTrade: (ticker: string, quantity: number, side: Side) => Promise<string | null>; // Error message or null
}

type Result = { kind: "ok" | "error"; text: string } | null;

/** Market-order entry: ticker, quantity, Buy / Sell. Instant fill, no confirmation. */
export default function TradeBar({ ticker, onTickerChange, price, onTrade }: Props) {
  const [qty, setQty] = useState("1");
  const [busy, setBusy] = useState<Side | null>(null);
  const [result, setResult] = useState<Result>(null);

  const quantity = Number(qty);
  const valid = ticker.trim().length > 0 && Number.isFinite(quantity) && quantity > 0;

  async function submit(side: Side, e?: FormEvent) {
    e?.preventDefault();
    if (!valid || busy) return;
    const symbol = ticker.trim().toUpperCase();
    setBusy(side);
    const err = await onTrade(symbol, quantity, side);
    setBusy(null);
    setResult(
      err
        ? { kind: "error", text: err }
        : { kind: "ok", text: `${side === "buy" ? "Bought" : "Sold"} ${fmtQty(quantity)} ${symbol}` },
    );
  }

  return (
    <form
      onSubmit={(e) => submit("buy", e)}
      className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2"
      aria-label="Trade"
    >
      <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-2">Trade</span>
      <input
        value={ticker}
        onChange={(e) => {
          onTickerChange(e.target.value.toUpperCase());
          setResult(null);
        }}
        aria-label="Trade ticker"
        placeholder="Ticker"
        maxLength={10}
        className="w-24 rounded border border-line bg-bg px-2 py-1 font-mono text-xs uppercase focus:border-blue focus:outline-none"
      />
      <input
        value={qty}
        onChange={(e) => {
          setQty(e.target.value);
          setResult(null);
        }}
        aria-label="Quantity"
        inputMode="decimal"
        type="number"
        min="0"
        step="any"
        className="w-24 rounded border border-line bg-bg px-2 py-1 font-mono text-xs focus:border-blue focus:outline-none"
      />
      <span className="font-mono text-[11px] text-ink-3">
        @ {fmtPrice(price)}
        {price != null && valid ? ` ≈ $${fmtPrice(price * quantity)}` : ""}
      </span>
      <button
        type="button"
        onClick={() => submit("buy")}
        disabled={!valid || busy !== null}
        className="rounded bg-up/90 px-3 py-1 text-xs font-semibold text-bg hover:bg-up disabled:opacity-40"
      >
        {busy === "buy" ? "Buying…" : "Buy"}
      </button>
      <button
        type="button"
        onClick={() => submit("sell")}
        disabled={!valid || busy !== null}
        className="rounded bg-down/90 px-3 py-1 text-xs font-semibold text-bg hover:bg-down disabled:opacity-40"
      >
        {busy === "sell" ? "Selling…" : "Sell"}
      </button>
      {result && (
        <span
          role="status"
          data-testid="trade-result"
          className={`text-[11px] ${result.kind === "ok" ? "text-up" : "text-down"}`}
        >
          {result.kind === "ok" ? "✓ " : "✕ "}
          {result.text}
        </span>
      )}
    </form>
  );
}
