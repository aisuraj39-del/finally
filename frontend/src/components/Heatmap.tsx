"use client";

import { useEffect, useRef, useState } from "react";

import { pnlColor } from "@/lib/colors";
import { fmtMoney, fmtPercent, fmtSignedMoney } from "@/lib/format";
import { squarify } from "@/lib/treemap";
import type { Position } from "@/lib/types";

const GAP = 2; // Surface gap between cells

function useSize<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setSize({ width: Math.floor(width), height: Math.floor(height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, size] as const;
}

/** Treemap of positions: area = portfolio weight, color = unrealized P&L %. */
export default function Heatmap({
  positions,
  onSelect,
}: {
  positions: Position[];
  onSelect: (ticker: string) => void;
}) {
  const [ref, { width, height }] = useSize<HTMLDivElement>();
  const [hover, setHover] = useState<string | null>(null);

  const rects = squarify(
    positions.map((p) => ({ ...p, id: p.ticker, value: p.market_value })),
    width,
    height,
  );
  const hovered = positions.find((p) => p.ticker === hover);

  return (
    <section className="flex h-full min-h-0 flex-col" aria-label="Portfolio heatmap">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-ink-2">Heatmap</h2>
        <span className="text-[10px] text-ink-3">size = weight · color = P&L % (±10%)</span>
      </div>
      <div ref={ref} className="relative min-h-0 flex-1 m-1" data-testid="heatmap">
        {positions.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-ink-3">
            No positions yet
          </div>
        )}
        {rects.map(({ item, x, y, w, h }) => {
          const big = w > 56 && h > 34;
          return (
            <button
              type="button"
              key={item.ticker}
              onClick={() => onSelect(item.ticker)}
              onMouseEnter={() => setHover(item.ticker)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(item.ticker)}
              onBlur={() => setHover(null)}
              data-testid={`heat-${item.ticker}`}
              data-pnl={item.unrealized_pnl_percent.toFixed(2)}
              aria-label={`${item.ticker}: ${fmtPercent(item.unrealized_pnl_percent)}, ${fmtPercent(item.weight * 100, 1)} of portfolio`}
              className="absolute flex flex-col items-start justify-start overflow-hidden rounded-[3px] p-1.5 text-left outline-none transition-[filter] hover:brightness-110 focus-visible:ring-1 focus-visible:ring-ink"
              style={{
                left: x + GAP / 2,
                top: y + GAP / 2,
                width: Math.max(w - GAP, 0),
                height: Math.max(h - GAP, 0),
                background: pnlColor(item.unrealized_pnl_percent),
              }}
            >
              {big && (
                <>
                  <span className="font-mono text-xs font-semibold text-ink">{item.ticker}</span>
                  <span className="font-mono text-[11px] text-ink/85">{fmtPercent(item.unrealized_pnl_percent)}</span>
                </>
              )}
              {!big && w > 28 && h > 16 && (
                <span className="font-mono text-[10px] font-semibold text-ink">{item.ticker}</span>
              )}
            </button>
          );
        })}
        {hovered && (
          <div className="pointer-events-none absolute bottom-1 left-1 z-10 rounded border border-line bg-panel-2/95 px-2 py-1 font-mono text-[11px] shadow">
            <div className="font-semibold">{hovered.ticker}</div>
            <div className="text-ink-2">
              {fmtMoney(hovered.market_value)} · {fmtPercent(hovered.weight * 100, 1)} weight
            </div>
            <div className="text-ink-2">
              P&L {fmtSignedMoney(hovered.unrealized_pnl)} ({fmtPercent(hovered.unrealized_pnl_percent)})
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
