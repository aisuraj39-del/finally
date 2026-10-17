"use client";

import { useEffect, useState, type ReactNode } from "react";

import { PriceStoreContext } from "@/hooks/usePrices";
import { PriceStore } from "@/lib/priceStore";

/** Owns the single app-wide SSE connection. */
export default function PriceProvider({ children }: { children: ReactNode }) {
  const [store] = useState(() => new PriceStore());

  useEffect(() => {
    store.connect();
    return () => store.disconnect();
  }, [store]);

  return <PriceStoreContext.Provider value={store}>{children}</PriceStoreContext.Provider>;
}
