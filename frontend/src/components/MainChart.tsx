"use client";

import { useMemo } from "react";

import { BLUE } from "@/lib/colors";
import { fmtPercent, fmtPrice, signOf } from "@/lib/format";
import type { PricePoint } from "@/lib/priceStore";
import type { PriceTick } from "@/lib/types";

import PriceCell from "./PriceCell";
import TimeSeriesChart from "./TimeSeriesChart";

const TONE = { up: "text-up", down: "text-down", flat: "text-ink-2" };
const formatPrice = (v: number) => fmtPrice(v);

export default function MainChart({
  ticker,
  tick,
  history,
}: {
  ticker: string | null;
  tick: PriceTick | undefined;
  history: PricePoint[] | undefined;
}) {
  const data = useMemo(() => (history ?? []).map((p) => ({ time: p.time, value: p.price })), [history]);
  const change = tick?.session_change_percent;

  return (
    <section className="flex h-full min-h-0 flex-col" aria-label="Price chart">
      <div className="flex items-baseline gap-3 border-b border-line px-3 py-2">
        <h2 className="font-mono text-sm font-semibold" data-testid="chart-ticker">
          {ticker ?? "—"}
        </h2>
        {tick && (
          <>
            <PriceCell price={tick.price} className="text-sm" />
            <span className={`font-mono text-xs ${TONE[signOf(change)]}`}>{fmtPercent(change)} today</span>
            <span className="ml-auto text-[10px] text-ink-3">
              Open {fmtPrice(tick.session_open)} · since page load
            </span>
          </>
        )}
      </div>
      <div className="min-h-0 flex-1 p-1">
        <TimeSeriesChart
          key={ticker ?? "none"}
          data={data}
          color={BLUE}
          formatValue={formatPrice}
          emptyText={ticker ? "Collecting prices…" : "Select a ticker"}
          ariaLabel={`${ticker ?? "No ticker"} price since page load`}
        />
      </div>
    </section>
  );
}
