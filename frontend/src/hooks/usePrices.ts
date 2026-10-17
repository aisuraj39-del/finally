"use client";

import { createContext, useContext, useSyncExternalStore } from "react";

import { PriceStore, type PriceState } from "@/lib/priceStore";

export const PriceStoreContext = createContext<PriceStore | null>(null);

const SERVER_STATE: PriceState = { prices: {}, history: {}, status: "reconnecting" };
const getServerSnapshot = () => SERVER_STATE;

/** Live prices, per-ticker history since page load, and connection status. */
export function usePrices(): PriceState {
  const store = useContext(PriceStoreContext);
  if (!store) throw new Error("usePrices must be used inside <PriceStoreContext>");
  return useSyncExternalStore(store.subscribe, store.getSnapshot, getServerSnapshot);
}
