"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { usePrices } from "@/hooks/usePrices";
import { ApiError, api, errorText } from "@/lib/api";
import { liveValuation } from "@/lib/portfolio";
import type { ChatMessage, Portfolio, Side, Snapshot, WatchlistEntry } from "@/lib/types";

import ChatPanel from "./ChatPanel";
import Header from "./Header";
import Heatmap from "./Heatmap";
import MainChart from "./MainChart";
import PnLChart from "./PnLChart";
import PositionsTable from "./PositionsTable";
import TradeBar from "./TradeBar";
import Watchlist from "./Watchlist";

const HISTORY_REFRESH_MS = 30_000; // Matches the backend snapshot interval

function messageOf(err: unknown): string {
  if (err instanceof ApiError) return err.code === "request_error" ? err.message : errorText(err.code);
  return "Something went wrong";
}

export default function Workstation() {
  const { prices, history, status } = usePrices();

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const [selectedState, setSelected] = useState<string | null>(null);
  const [tradeTickerState, setTradeTicker] = useState<string | null>(null);

  const selected = selectedState ?? watchlist[0]?.ticker ?? null;
  const tradeTicker = tradeTickerState ?? selected ?? "";

  const loadPortfolio = useCallback(() => api.getPortfolio().then(setPortfolio).catch(() => {}), []);
  const loadWatchlist = useCallback(
    () => api.getWatchlist().then((r) => setWatchlist(r.tickers)).catch(() => {}),
    [],
  );
  const loadHistory = useCallback(
    () => api.getHistory().then((r) => setSnapshots(r.snapshots)).catch(() => {}),
    [],
  );

  useEffect(() => {
    loadPortfolio();
    loadWatchlist();
    loadHistory();
    api
      .getChatHistory()
      .then((r) => setMessages(r.messages))
      .catch(() => {});
    const timer = setInterval(loadHistory, HISTORY_REFRESH_MS);
    return () => clearInterval(timer);
  }, [loadPortfolio, loadWatchlist, loadHistory]);

  const live = useMemo(() => liveValuation(portfolio, prices), [portfolio, prices]);

  const select = useCallback((ticker: string) => {
    setSelected(ticker);
    setTradeTicker(ticker);
  }, []);

  const trade = useCallback(
    async (ticker: string, quantity: number, side: Side) => {
      try {
        const res = await api.trade(ticker, quantity, side);
        setPortfolio(res.portfolio);
        loadHistory();
        return null;
      } catch (err) {
        return messageOf(err);
      }
    },
    [loadHistory],
  );

  const addTicker = useCallback(
    async (ticker: string) => {
      try {
        await api.addTicker(ticker);
        await loadWatchlist();
        return null;
      } catch (err) {
        return messageOf(err);
      }
    },
    [loadWatchlist],
  );

  const removeTicker = useCallback(
    async (ticker: string) => {
      setWatchlist((w) => w.filter((e) => e.ticker !== ticker)); // Optimistic
      if (selectedState === ticker) setSelected(null);
      try {
        await api.removeTicker(ticker);
      } finally {
        loadWatchlist();
      }
    },
    [loadWatchlist, selectedState],
  );

  const sendChat = useCallback(
    async (text: string) => {
      setChatError(null);
      setChatLoading(true);
      const pending: ChatMessage = {
        id: `local-${Date.now()}`,
        role: "user",
        content: text,
        actions: null,
        created_at: new Date().toISOString(),
      };
      setMessages((m) => [...m, pending]);
      try {
        const reply = await api.chat(text);
        setMessages((m) => [
          ...m,
          { id: reply.id, role: "assistant", content: reply.message, actions: reply.actions, created_at: reply.created_at },
        ]);
        if (reply.actions.trades.length || reply.actions.watchlist_changes.length) {
          loadPortfolio();
          loadWatchlist();
          loadHistory();
        }
      } catch (err) {
        setChatError(messageOf(err));
      } finally {
        setChatLoading(false);
      }
    },
    [loadPortfolio, loadWatchlist, loadHistory],
  );

  const positions = live?.positions ?? [];

  return (
    <div className="flex h-full flex-col">
      <Header portfolio={live} status={status} />

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto lg:flex-row lg:overflow-hidden">
        {/* Left: watchlist */}
        <div className="flex max-h-[45vh] min-h-0 shrink-0 flex-col border-b border-line bg-panel lg:max-h-none lg:w-[260px] xl:w-[300px] lg:border-b-0 lg:border-r">
          <Watchlist
            entries={watchlist}
            prices={prices}
            history={history}
            selected={selected}
            onSelect={select}
            onAdd={addTicker}
            onRemove={removeTicker}
          />
        </div>

        {/* Center: chart, trade bar, heatmap + P&L, positions */}
        {/* Stacked (<lg): natural height so the page scrolls. Side by side: fill the row. */}
        <main className="grid min-w-0 shrink-0 grid-rows-[minmax(260px,1fr)_auto_minmax(220px,0.8fr)_minmax(160px,0.7fr)] bg-bg lg:min-h-0 lg:flex-1 lg:shrink">
          <div className="min-h-0 border-b border-line bg-panel">
            <MainChart
              ticker={selected}
              tick={selected ? prices[selected] : undefined}
              history={selected ? history[selected] : undefined}
            />
          </div>
          <div className="bg-panel">
            <TradeBar
              ticker={tradeTicker}
              onTickerChange={setTradeTicker}
              price={prices[tradeTicker]?.price ?? null}
              onTrade={trade}
            />
          </div>
          <div className="grid min-h-0 grid-cols-1 border-b border-line md:grid-cols-2">
            <div className="min-h-0 border-line bg-panel md:border-r">
              <Heatmap positions={positions} onSelect={select} />
            </div>
            <div className="min-h-0 bg-panel">
              <PnLChart snapshots={snapshots} />
            </div>
          </div>
          <div className="min-h-0 bg-panel">
            <PositionsTable positions={positions} onSelect={select} />
          </div>
        </main>

        {/* Right: AI chat */}
        <div className={`flex min-h-0 shrink-0 ${chatCollapsed ? "" : "h-[60vh] lg:h-auto"}`}>
          <ChatPanel
            messages={messages}
            loading={chatLoading}
            error={chatError}
            onSend={sendChat}
            collapsed={chatCollapsed}
            onToggle={() => setChatCollapsed((c) => !c)}
          />
        </div>
      </div>
    </div>
  );
}
