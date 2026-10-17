"use client";

import { useEffect, useRef } from "react";

import { fmtPrice } from "@/lib/format";

const FLASH_MS = 120; // Time the highlight is held before fading out over 500ms (CSS)

/**
 * Price that briefly flashes green/red when it changes (PLAN §2).
 * The class is toggled directly on the DOM node, so a tick doesn't re-render.
 */
export default function PriceCell({ price, className = "" }: { price: number | null; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const prev = useRef<number | null>(price);

  useEffect(() => {
    const el = ref.current;
    const before = prev.current;
    prev.current = price;
    if (!el || price == null || before == null || price === before) return;

    const cls = price > before ? "flash-up" : "flash-down";
    el.classList.remove("flash-up", "flash-down");
    el.classList.add(cls);
    const timer = setTimeout(() => el.classList.remove(cls), FLASH_MS);
    return () => clearTimeout(timer);
  }, [price]);

  return (
    <span ref={ref} className={`flash-cell rounded px-1 font-mono ${className}`} data-testid="price">
      {fmtPrice(price)}
    </span>
  );
}
