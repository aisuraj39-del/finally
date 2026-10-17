"use client";

import { useState, type FormEvent } from "react";

import { fmtPercent, signOf } from "@/lib/format";
import type { PricePoint } from "@/lib/priceStore";
import type { PriceMap, WatchlistEntry } from "@/lib/types";

import PriceCell from "./PriceCell";
import Sparkline from "./Sparkline";

const TONE = { up: "text-up", down: "text-down", flat: "text-ink-2" };

interface Props {
  entries: WatchlistEntry[];
  prices: PriceMap;
  history: Record<string, PricePoint[]>;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<string | null>; // Resolves to an error message or null
  onRemove: (ticker: string) => void;
}

export default function Watchlist({ entries, prices, history, selected, onSelect, onAdd, onRemove }: Props) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    setBusy(true);
    const err = await onAdd(ticker);
    setBusy(false);
    setError(err);
    if (!err) setInput("");
  }

  return (
    <section className="flex h-full min-h-0 flex-col" aria-label="Watchlist">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-ink-2">Watchlist</h2>
        <span className="text-[10px] text-ink-3">{entries.length} tickers</span>
      </div>

      <form onSubmit={submit} className="flex gap-1 border-b border-line p-2">
        <input
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setError(null);
          }}
          placeholder="Add ticker…"
          aria-label="Ticker to add"
          maxLength={10}
          className="min-w-0 flex-1 rounded border border-line bg-bg px-2 py-1 font-mono text-xs uppercase placeholder:normal-case placeholder:text-ink-3 focus:border-blue focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded bg-purple px-2 py-1 text-xs font-medium text-white hover:bg-purple-hover disabled:opacity-40"
        >
          Add
        </button>
      </form>
      {error && (
        <p role="alert" className="border-b border-line px-3 py-1 text-[11px] text-down">
          {error}
        </p>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-panel text-[10px] uppercase tracking-wider text-ink-3">
            <tr>
              <th className="px-3 py-1.5 text-left font-medium">Ticker</th>
              <th className="px-1 py-1.5 text-right font-medium">Price</th>
              <th className="px-1 py-1.5 text-right font-medium">Day</th>
              <th className="py-1.5 pr-2 font-medium" aria-label="Trend" />
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => {
              const tick = prices[entry.ticker];
              const price = tick?.price ?? entry.price;
              const change = tick?.session_change_percent ?? entry.session_change_percent;
              const isSelected = entry.ticker === selected;
              return (
                <tr
                  key={entry.ticker}
                  onClick={() => onSelect(entry.ticker)}
                  aria-selected={isSelected}
                  data-testid={`watch-${entry.ticker}`}
                  className={`group cursor-pointer border-b border-line/60 hover:bg-panel-2 ${
                    isSelected ? "bg-panel-2 shadow-[inset_2px_0_0_var(--color-blue)]" : ""
                  }`}
                >
                  <td className="px-3 py-1.5 font-mono font-semibold">{entry.ticker}</td>
                  <td className="px-1 py-1.5 text-right">
                    <PriceCell price={price} />
                  </td>
                  <td className={`px-1 py-1.5 text-right font-mono ${TONE[signOf(change)]}`}>
                    {fmtPercent(change)}
                  </td>
                  <td className="relative py-1 pr-2">
                    <div className="flex justify-end">
                      <Sparkline points={history[entry.ticker]} width={72} height={22} />
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemove(entry.ticker);
                      }}
                      aria-label={`Remove ${entry.ticker}`}
                      className="absolute right-1 top-1/2 hidden -translate-y-1/2 rounded bg-panel-2 px-1.5 text-ink-3 hover:text-down group-hover:block focus:block"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {entries.length === 0 && <p className="p-4 text-center text-xs text-ink-3">No tickers. Add one above.</p>}
      </div>
    </section>
  );
}
