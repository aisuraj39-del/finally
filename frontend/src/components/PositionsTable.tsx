"use client";

import { fmtMoney, fmtPercent, fmtPrice, fmtQty, fmtSignedMoney, signOf } from "@/lib/format";
import type { Position } from "@/lib/types";

import PriceCell from "./PriceCell";

const TONE = { up: "text-up", down: "text-down", flat: "text-ink-2" };

export default function PositionsTable({
  positions,
  onSelect,
}: {
  positions: Position[];
  onSelect: (ticker: string) => void;
}) {
  return (
    <section className="flex h-full min-h-0 flex-col" aria-label="Positions">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-ink-2">Positions</h2>
        <span className="text-[10px] text-ink-3">{positions.length} open</span>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full text-xs" data-testid="positions-table">
          <thead className="sticky top-0 bg-panel text-[10px] uppercase tracking-wider text-ink-3">
            <tr>
              <th className="px-3 py-1.5 text-left font-medium">Ticker</th>
              <th className="px-2 py-1.5 text-right font-medium">Qty</th>
              <th className="px-2 py-1.5 text-right font-medium">Avg cost</th>
              <th className="px-2 py-1.5 text-right font-medium">Price</th>
              <th className="px-2 py-1.5 text-right font-medium">Value</th>
              <th className="px-2 py-1.5 text-right font-medium">Unrealized P&L</th>
              <th className="px-3 py-1.5 text-right font-medium">%</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => {
              const tone = TONE[signOf(p.unrealized_pnl)];
              return (
                <tr
                  key={p.ticker}
                  onClick={() => onSelect(p.ticker)}
                  data-testid={`position-${p.ticker}`}
                  className="cursor-pointer border-b border-line/60 font-mono hover:bg-panel-2"
                >
                  <td className="px-3 py-1.5 font-semibold">{p.ticker}</td>
                  <td className="px-2 py-1.5 text-right" data-testid="qty">{fmtQty(p.quantity)}</td>
                  <td className="px-2 py-1.5 text-right text-ink-2">{fmtPrice(p.avg_cost)}</td>
                  <td className="px-2 py-1.5 text-right"><PriceCell price={p.current_price} /></td>
                  <td className="px-2 py-1.5 text-right">{fmtMoney(p.market_value)}</td>
                  <td className={`px-2 py-1.5 text-right ${tone}`}>{fmtSignedMoney(p.unrealized_pnl)}</td>
                  <td className={`px-3 py-1.5 text-right ${tone}`}>{fmtPercent(p.unrealized_pnl_percent)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {positions.length === 0 && (
          <p className="p-4 text-center text-xs text-ink-3">No positions. Use the trade bar or ask the assistant.</p>
        )}
      </div>
    </section>
  );
}
