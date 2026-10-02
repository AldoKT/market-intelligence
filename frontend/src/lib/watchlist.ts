import { useEffect, useState } from "react";

const KEY = "signal_watchlist_v1";
const EVENT = "signal-watchlist-change";

function readWatchlist(): string[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(KEY);

    if (!raw) return [];

    const parsed = JSON.parse(raw);

    if (!Array.isArray(parsed)) return [];

    return parsed
      .map((value) => String(value).toUpperCase())
      .filter(Boolean);
  } catch {
    return [];
  }
}

function writeWatchlist(symbols: string[]) {
  const clean = Array.from(
    new Set(symbols.map((symbol) => symbol.toUpperCase()))
  );

  window.localStorage.setItem(KEY, JSON.stringify(clean));
  window.dispatchEvent(new Event(EVENT));
}

export function toggleWatchlist(symbol: string) {
  const current = readWatchlist();
  const clean = symbol.toUpperCase();

  if (current.includes(clean)) {
    writeWatchlist(current.filter((item) => item !== clean));
  } else {
    writeWatchlist([...current, clean]);
  }
}

export function useWatchlist() {
  const [symbols, setSymbols] = useState<string[]>(() => readWatchlist());

  useEffect(() => {
    const sync = () => setSymbols(readWatchlist());

    window.addEventListener("storage", sync);
    window.addEventListener(EVENT, sync);

    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener(EVENT, sync);
    };
  }, []);

  return {
    symbols,
    has: (symbol: string) => symbols.includes(symbol.toUpperCase()),
    toggle: toggleWatchlist
  };
}
