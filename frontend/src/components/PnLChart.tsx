"use client";

import { useMemo } from "react";

import { YELLOW } from "@/lib/colors";
import { fmtMoney } from "@/lib/format";
import type { Snapshot } from "@/lib/types";

import TimeSeriesChart, { type Point } from "./TimeSeriesChart";

/** Snapshots to strictly increasing per-second points (last value wins per second). */
export function snapshotsToPoints(snapshots: Snapshot[]): Point[] {
  const out: Point[] = [];
  for (const s of snapshots) {
    const time = Math.floor(Date.parse(s.recorded_at) / 1000);
    if (!Number.isFinite(time)) continue;
    const last = out[out.length - 1];
    if (last && last.time === time) last.value = s.total_value;
    else if (!last || time > last.time) out.push({ time, value: s.total_value });
  }
  return out;
}

const formatMoney = (v: number) => fmtMoney(v);

/** Total portfolio value from portfolio_snapshots (every 30s and after each trade). */
export default function PnLChart({ snapshots }: { snapshots: Snapshot[] }) {
  const data = useMemo(() => snapshotsToPoints(snapshots), [snapshots]);

  return (
    <section className="flex h-full min-h-0 flex-col" aria-label="Portfolio value chart">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-ink-2">Portfolio value</h2>
        <span className="text-[10px] text-ink-3" data-testid="pnl-points" data-count={data.length}>
          {data.length} snapshots · 24h
        </span>
      </div>
      <div className="min-h-0 flex-1 p-1" data-testid="pnl-chart">
        <TimeSeriesChart
          data={data}
          color={YELLOW}
          formatValue={formatMoney}
          emptyText="Snapshots every 30s — data appears shortly"
          ariaLabel="Total portfolio value over time"
        />
      </div>
    </section>
  );
}
