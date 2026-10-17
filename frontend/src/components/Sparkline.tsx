import { DOWN, UP } from "@/lib/colors";
import type { PricePoint } from "@/lib/priceStore";

const MAX_POINTS = 120; // Last ~60s at 500ms keeps the sparkline readable

/** Tiny SVG line of price since page load; colored by direction over the window. */
export default function Sparkline({
  points,
  width = 80,
  height = 24,
}: {
  points: PricePoint[] | undefined;
  width?: number;
  height?: number;
}) {
  const data = (points ?? []).slice(-MAX_POINTS);
  if (data.length < 2) {
    return <svg width={width} height={height} aria-hidden data-testid="sparkline" />;
  }

  const prices = data.map((p) => p.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const pad = 2;
  const step = (width - pad * 2) / (data.length - 1);
  const d = data
    .map((p, i) => {
      const x = pad + i * step;
      const y = pad + (height - pad * 2) * (1 - (p.price - min) / range);
      return `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join("");
  const color = prices[prices.length - 1] >= prices[0] ? UP : DOWN;

  return (
    <svg width={width} height={height} aria-hidden data-testid="sparkline" data-points={data.length}>
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
