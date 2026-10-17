"use client";

import {
  AreaSeries,
  ColorType,
  CrosshairMode,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";

export interface Point {
  time: number; // Unix seconds, strictly increasing
  value: number;
}

interface Props {
  data: Point[];
  color: string;
  formatValue: (v: number) => string;
  emptyText: string;
  ariaLabel: string;
}

function withAlpha(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

const timeFmt = new Intl.DateTimeFormat("en-US", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

/** Single-series area chart (canvas) with a crosshair and a hover readout. */
export default function TimeSeriesChart({ data, color, formatValue, emptyText, ariaLabel }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const lastRef = useRef<{ first: number; length: number } | null>(null);
  const [hover, setHover] = useState<Point | null>(null);

  // Create the chart once
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#6b7785",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: "rgba(34, 43, 56, 0.6)" },
      },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.15, bottom: 0.1 } },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: true },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: "#2f3a4a", labelBackgroundColor: "#2f3a4a" },
        horzLine: { color: "#2f3a4a", labelBackgroundColor: "#2f3a4a" },
      },
      localization: {
        priceFormatter: formatValue,
        timeFormatter: (t: number) => timeFmt.format(new Date(t * 1000)),
      },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addSeries(AreaSeries, {
      lineColor: color,
      lineWidth: 2,
      topColor: withAlpha(color, 0.25),
      bottomColor: withAlpha(color, 0),
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerRadius: 4,
    });

    const onMove = (param: MouseEventParams) => {
      const d = param.seriesData.get(series) as { value?: number } | undefined;
      if (param.time === undefined || d?.value === undefined) setHover(null);
      else setHover({ time: param.time as number, value: d.value });
    };
    chart.subscribeCrosshairMove(onMove);

    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.unsubscribeCrosshairMove(onMove);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      lastRef.current = null;
    };
    // Recreate only if the color or formatter identity changes
  }, [color, formatValue]);

  // Push data: append with update() when possible, otherwise replace
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    const prev = lastRef.current;
    const first = data[0]?.time ?? 0;
    const toSeries = (p: Point) => ({ time: p.time as UTCTimestamp, value: p.value });

    const grew = prev ? data.length - prev.length : -1;
    // Same series start and at most one new point: cheap incremental update
    if (prev && prev.first === first && data.length > 0 && (grew === 0 || grew === 1)) {
      series.update(toSeries(data[data.length - 1]));
    } else {
      series.setData(data.map(toSeries));
    }
    if (grew !== 0) chartRef.current?.timeScale().fitContent(); // Keep all history in view
    lastRef.current = { first, length: data.length };
  }, [data]);

  return (
    <div className="relative h-full w-full" role="img" aria-label={ariaLabel}>
      <div ref={containerRef} className="absolute inset-0" />
      {hover && (
        <div className="pointer-events-none absolute left-2 top-1 rounded border border-line bg-panel-2/90 px-2 py-1 font-mono text-[11px] text-ink">
          <span className="text-ink-3">{timeFmt.format(new Date(hover.time * 1000))}</span>{" "}
          {formatValue(hover.value)}
        </div>
      )}
      {data.length < 2 && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-ink-3">
          {emptyText}
        </div>
      )}
    </div>
  );
}
