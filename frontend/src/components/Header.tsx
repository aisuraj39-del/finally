"use client";

import { fmtMoney, fmtPercent, fmtSignedMoney, signOf } from "@/lib/format";
import type { ConnectionStatus, Portfolio } from "@/lib/types";

const STATUS: Record<ConnectionStatus, { dot: string; label: string }> = {
  connected: { dot: "bg-up", label: "Live" },
  reconnecting: { dot: "bg-accent", label: "Reconnecting" },
  disconnected: { dot: "bg-down", label: "Disconnected" },
};

const TONE = { up: "text-up", down: "text-down", flat: "text-ink-2" };

function Stat({ label, value, tone, testId }: { label: string; value: string; tone?: string; testId?: string }) {
  return (
    <div className="flex flex-col leading-tight">
      <span className="text-[10px] uppercase tracking-wider text-ink-3">{label}</span>
      <span className={`font-mono text-sm font-medium ${tone ?? "text-ink"}`} data-testid={testId}>
        {value}
      </span>
    </div>
  );
}

export default function Header({ portfolio, status }: { portfolio: Portfolio | null; status: ConnectionStatus }) {
  const pnlTone = TONE[signOf(portfolio?.unrealized_pnl)];
  const s = STATUS[status];

  return (
    <header className="flex h-12 shrink-0 items-center gap-6 border-b border-line bg-panel px-4">
      <div className="flex items-baseline gap-2">
        <span className="text-base font-semibold tracking-tight">
          Fin<span className="text-accent">Ally</span>
        </span>
        <span className="hidden text-[10px] uppercase tracking-widest text-ink-3 sm:inline">AI Trading Workstation</span>
      </div>

      <div className="ml-auto flex items-center gap-6">
        <Stat label="Portfolio" value={fmtMoney(portfolio?.total_value)} testId="total-value" />
        <Stat label="Cash" value={fmtMoney(portfolio?.cash_balance)} testId="cash-balance" />
        <Stat
          label="Unrealized P&L"
          value={
            portfolio
              ? `${fmtSignedMoney(portfolio.unrealized_pnl)} (${fmtPercent(portfolio.unrealized_pnl_percent)})`
              : "—"
          }
          tone={pnlTone}
        />
        <div
          className="flex items-center gap-2 rounded border border-line px-2 py-1"
          title={`Price stream: ${s.label}`}
          data-testid="connection-status"
          data-status={status}
        >
          <span className={`h-2 w-2 rounded-full ${s.dot}`} aria-hidden />
          <span className="text-[11px] text-ink-2">{s.label}</span>
        </div>
      </div>
    </header>
  );
}
