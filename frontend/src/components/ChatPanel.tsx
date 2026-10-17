"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import { errorText } from "@/lib/api";
import { fmtPrice, fmtQty } from "@/lib/format";
import type { ChatActions, ChatMessage } from "@/lib/types";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  onSend: (text: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}

function Actions({ actions }: { actions: ChatActions | null }) {
  if (!actions || (!actions.trades.length && !actions.watchlist_changes.length)) return null;
  return (
    <ul className="mt-2 space-y-1" data-testid="chat-actions">
      {actions.watchlist_changes.map((w, i) => (
        <li
          key={`w${i}`}
          className={`rounded border px-2 py-1 font-mono text-[11px] ${
            w.status === "executed" ? "border-blue/40 text-blue" : "border-down/40 text-down"
          }`}
        >
          {w.status === "executed" ? "✓" : "✕"} Watchlist {w.action} {w.ticker}
          {w.status === "failed" && ` — ${errorText(w.error)}`}
        </li>
      ))}
      {actions.trades.map((t, i) => (
        <li
          key={`t${i}`}
          data-testid="chat-trade"
          data-status={t.status}
          className={`rounded border px-2 py-1 font-mono text-[11px] ${
            t.status === "executed" ? "border-up/40 text-up" : "border-down/40 text-down"
          }`}
        >
          {t.status === "executed"
            ? `✓ ${t.side === "buy" ? "Bought" : "Sold"} ${fmtQty(t.quantity)} ${t.ticker} @ ${fmtPrice(t.price)}`
            : `✕ ${t.side === "buy" ? "Buy" : "Sell"} ${fmtQty(t.quantity)} ${t.ticker} failed — ${errorText(t.error)}`}
        </li>
      ))}
    </ul>
  );
}

export default function ChatPanel({ messages, loading, error, onSend, collapsed, onToggle }: Props) {
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    onSend(text);
    setInput("");
  }

  if (collapsed) {
    return (
      <aside className="flex w-10 shrink-0 flex-col items-center border-l border-line bg-panel py-2">
        <button
          type="button"
          onClick={onToggle}
          aria-label="Open AI assistant"
          className="rounded px-1 py-2 text-[11px] font-semibold uppercase tracking-wider text-accent [writing-mode:vertical-rl] hover:bg-panel-2"
        >
          AI Assistant
        </button>
      </aside>
    );
  }

  return (
    <aside
      className="flex min-h-0 w-full shrink-0 flex-col border-l border-line bg-panel lg:w-[300px] xl:w-[360px]"
      aria-label="AI assistant"
    >
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-accent">FinAlly AI</h2>
        <button
          type="button"
          onClick={onToggle}
          aria-label="Collapse AI assistant"
          className="rounded px-1.5 text-ink-3 hover:bg-panel-2 hover:text-ink"
        >
          »
        </button>
      </div>

      <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3" data-testid="chat-messages">
        {messages.length === 0 && !loading && (
          <div className="space-y-2 text-xs text-ink-3">
            <p>Ask about your portfolio, or tell me to trade. For example:</p>
            <ul className="space-y-1 font-mono text-[11px] text-ink-2">
              <li>“How concentrated is my portfolio?”</li>
              <li>“Buy 5 NVDA”</li>
              <li>“Add PYPL to my watchlist”</li>
            </ul>
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            data-testid={`chat-${m.role}`}
            className={m.role === "user" ? "ml-8 flex justify-end" : "mr-4"}
          >
            <div
              className={`rounded px-3 py-2 text-xs leading-relaxed ${
                m.role === "user" ? "bg-blue/15 text-ink" : "border border-line bg-panel-2 text-ink"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.role === "assistant" && <Actions actions={m.actions} />}
            </div>
          </div>
        ))}
        {loading && (
          <div className="mr-4 flex items-center gap-1 rounded border border-line bg-panel-2 px-3 py-2" data-testid="chat-loading">
            <span className="sr-only">Assistant is thinking</span>
            {[0, 150, 300].map((d) => (
              <span
                key={d}
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent"
                style={{ animationDelay: `${d}ms` }}
                aria-hidden
              />
            ))}
          </div>
        )}
        {error && (
          <p role="alert" className="rounded border border-down/40 px-3 py-2 text-xs text-down">
            {error}
          </p>
        )}
      </div>

      <form onSubmit={submit} className="flex gap-2 border-t border-line p-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask FinAlly…"
          aria-label="Message"
          maxLength={4000}
          className="min-w-0 flex-1 rounded border border-line bg-bg px-2 py-1.5 text-xs placeholder:text-ink-3 focus:border-blue focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded bg-purple px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-hover disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </aside>
  );
}
