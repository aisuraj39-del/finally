import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ChatMessage, ConnectionStatus, Portfolio, Position, WatchlistEntry } from "@/lib/types";

import ChatPanel from "./ChatPanel";
import Header from "./Header";
import PositionsTable from "./PositionsTable";
import PriceCell from "./PriceCell";
import { snapshotsToPoints } from "./PnLChart";
import Watchlist from "./Watchlist";

describe("PriceCell", () => {
  it("flashes green on an uptick and red on a downtick, then clears", () => {
    vi.useFakeTimers();
    const { rerender } = render(<PriceCell price={100} />);
    const el = screen.getByTestId("price");
    expect(el).toHaveTextContent("100.00");
    expect(el.className).not.toMatch(/flash-(up|down)/);

    rerender(<PriceCell price={101} />);
    expect(el).toHaveClass("flash-up");
    act(() => vi.advanceTimersByTime(200));
    expect(el).not.toHaveClass("flash-up");

    rerender(<PriceCell price={99} />);
    expect(el).toHaveClass("flash-down");
    vi.useRealTimers();
  });

  it("does not flash when the price is unchanged", () => {
    const { rerender } = render(<PriceCell price={100} />);
    rerender(<PriceCell price={100} />);
    expect(screen.getByTestId("price").className).not.toMatch(/flash-(up|down)/);
  });
});

const entry = (ticker: string, price: number | null): WatchlistEntry => ({
  ticker, price, previous_price: price, session_open: price, session_change_percent: 0,
  direction: "flat", added_at: "2026-01-01T00:00:00Z",
});

describe("Watchlist", () => {
  const baseProps = {
    entries: [entry("AAPL", 190), entry("TSLA", 250)],
    prices: {},
    history: {},
    selected: "AAPL",
    onSelect: vi.fn(),
    onAdd: vi.fn(async () => null),
    onRemove: vi.fn(),
  };

  it("renders rows with prices and marks the selection", () => {
    render(<Watchlist {...baseProps} />);
    const row = screen.getByTestId("watch-AAPL");
    expect(within(row).getByTestId("price")).toHaveTextContent("190.00");
    expect(row).toHaveAttribute("aria-selected", "true");
  });

  it("selects a ticker on click", async () => {
    const onSelect = vi.fn();
    render(<Watchlist {...baseProps} onSelect={onSelect} />);
    await userEvent.click(screen.getByTestId("watch-TSLA"));
    expect(onSelect).toHaveBeenCalledWith("TSLA");
  });

  it("adds an uppercased ticker and clears the input", async () => {
    const onAdd = vi.fn(async () => null);
    render(<Watchlist {...baseProps} onAdd={onAdd} />);
    const input = screen.getByLabelText("Ticker to add");
    await userEvent.type(input, "pypl{Enter}");
    expect(onAdd).toHaveBeenCalledWith("PYPL");
    expect(input).toHaveValue("");
  });

  it("shows the error when adding fails", async () => {
    render(<Watchlist {...baseProps} onAdd={vi.fn(async () => "Already on watchlist")} />);
    await userEvent.type(screen.getByLabelText("Ticker to add"), "AAPL{Enter}");
    expect(screen.getByRole("alert")).toHaveTextContent("Already on watchlist");
  });

  it("removes without selecting the row", async () => {
    const onRemove = vi.fn();
    const onSelect = vi.fn();
    render(<Watchlist {...baseProps} onRemove={onRemove} onSelect={onSelect} />);
    await userEvent.click(screen.getByLabelText("Remove TSLA"));
    expect(onRemove).toHaveBeenCalledWith("TSLA");
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("prefers the streamed price over the API price", () => {
    const prices = {
      AAPL: { ticker: "AAPL", price: 195.5, previous_price: 195, session_open: 190, timestamp: 1,
              change: 0.5, change_percent: 0.26, session_change_percent: 2.89, direction: "up" as const },
    };
    render(<Watchlist {...baseProps} prices={prices} />);
    const row = screen.getByTestId("watch-AAPL");
    expect(within(row).getByTestId("price")).toHaveTextContent("195.50");
    expect(row).toHaveTextContent("+2.89%");
  });
});

describe("Header", () => {
  const portfolio: Portfolio = {
    cash_balance: 8000, positions_value: 2300, total_value: 10300,
    unrealized_pnl: 300, unrealized_pnl_percent: 15, positions: [],
  };

  it("shows totals and connection status", () => {
    render(<Header portfolio={portfolio} status="connected" />);
    expect(screen.getByTestId("total-value")).toHaveTextContent("$10,300.00");
    expect(screen.getByTestId("cash-balance")).toHaveTextContent("$8,000.00");
    expect(screen.getByText("+$300.00 (+15.00%)")).toBeInTheDocument();
    expect(screen.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
  });

  it.each<[ConnectionStatus, string]>([
    ["reconnecting", "Reconnecting"],
    ["disconnected", "Disconnected"],
  ])("labels %s", (status, label) => {
    render(<Header portfolio={null} status={status} />);
    expect(screen.getByTestId("connection-status")).toHaveTextContent(label);
  });
});

describe("PositionsTable", () => {
  const position: Position = {
    ticker: "AAPL", quantity: 10, avg_cost: 100, current_price: 90, market_value: 900,
    unrealized_pnl: -100, unrealized_pnl_percent: -10, weight: 0.09,
  };

  it("renders a position with signed P&L", () => {
    render(<PositionsTable positions={[position]} onSelect={vi.fn()} />);
    const row = screen.getByTestId("position-AAPL");
    expect(row).toHaveTextContent("−$100.00");
    expect(row).toHaveTextContent("−10.00%");
    expect(within(row).getByTestId("qty")).toHaveTextContent("10");
  });

  it("shows an empty state", () => {
    render(<PositionsTable positions={[]} onSelect={vi.fn()} />);
    expect(screen.getByText(/No positions/)).toBeInTheDocument();
  });
});

describe("ChatPanel", () => {
  const messages: ChatMessage[] = [
    { id: "1", role: "user", content: "buy 5 AAPL", actions: null, created_at: "" },
    {
      id: "2", role: "assistant", content: "Buying 5 AAPL.", created_at: "",
      actions: {
        trades: [
          { ticker: "AAPL", side: "buy", quantity: 5, status: "executed", price: 190.5, error: null },
          { ticker: "TSLA", side: "sell", quantity: 2, status: "failed", price: null, error: "insufficient_shares" },
        ],
        watchlist_changes: [{ ticker: "PYPL", action: "add", status: "executed", error: null }],
      },
    },
  ];
  const props = { messages, loading: false, error: null, onSend: vi.fn(), collapsed: false, onToggle: vi.fn() };

  it("renders messages with inline action confirmations", () => {
    render(<ChatPanel {...props} />);
    expect(screen.getByTestId("chat-user")).toHaveTextContent("buy 5 AAPL");
    const trades = screen.getAllByTestId("chat-trade");
    expect(trades[0]).toHaveTextContent("✓ Bought 5 AAPL @ 190.50");
    expect(trades[1]).toHaveTextContent("✕ Sell 2 TSLA failed — Not enough shares");
    expect(screen.getByText(/Watchlist add PYPL/)).toBeInTheDocument();
  });

  it("shows a loading indicator and disables sending while waiting", async () => {
    render(<ChatPanel {...props} loading />);
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Message"), "hi");
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("sends trimmed text and clears the input", async () => {
    const onSend = vi.fn();
    render(<ChatPanel {...props} onSend={onSend} />);
    await userEvent.type(screen.getByLabelText("Message"), "  how am I doing?  {Enter}");
    expect(onSend).toHaveBeenCalledWith("how am I doing?");
    expect(screen.getByLabelText("Message")).toHaveValue("");
  });

  it("collapses to a rail", () => {
    render(<ChatPanel {...props} collapsed />);
    expect(screen.getByLabelText("Open AI assistant")).toBeInTheDocument();
    expect(screen.queryByTestId("chat-messages")).not.toBeInTheDocument();
  });
});

describe("snapshotsToPoints", () => {
  it("orders by second and keeps the last value per second", () => {
    const points = snapshotsToPoints([
      { total_value: 1, recorded_at: "2026-01-01T00:00:00.100000Z" },
      { total_value: 2, recorded_at: "2026-01-01T00:00:00.900000Z" },
      { total_value: 3, recorded_at: "2026-01-01T00:00:30.000000Z" },
    ]);
    expect(points.map((p) => p.value)).toEqual([2, 3]);
    expect(points[1].time - points[0].time).toBe(30);
  });
});
