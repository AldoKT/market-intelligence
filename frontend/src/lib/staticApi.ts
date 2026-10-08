import type {BrokerHistory, BrokerHistoryPoint} from "./brokerTypes";

const cache = new Map<string, Promise<unknown>>();
async function read<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    const pending = fetch(`${import.meta.env.BASE_URL}data/${path}`).then(async response => {
      if (!response.ok) throw new Error(`SIGNAL demo ${response.status}: data unavailable`);
      return response.json();
    }).catch(error => { cache.delete(path); throw error; });
    cache.set(path, pending);
  }
  return cache.get(path) as Promise<T>;
}
export async function getStaticJson<T>(path: string): Promise<T> {
  const url = new URL(path, "https://signal.local");
  const parts = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const [, section, symbol, detail, identifier] = parts;
  if (section === "investigations") {
    if (symbol) return read<T>(`product/tickers/${encodeURIComponent(symbol)}/${detail ?? "investigation"}.json`);
    const payload = await read<{items: Record<string, unknown>[]; count: number}>("product/investigations.json");
    const items = payload.items.filter(item => {
      for (const key of ["state", "peer_group", "context_scope"]) {
        const value = url.searchParams.get(key);
        if (value && item[key] !== value) return false;
      }
      const active = url.searchParams.get("active");
      if (active !== null && item.active !== (active === "true")) return false;
      const q = url.searchParams.get("q")?.trim().toUpperCase();
      return !q || String(item.symbol ?? "").toUpperCase().includes(q);
    });
    return {...payload, items, count: items.length} as T;
  }
  if (section === "brokers") {
    const safeSymbol = encodeURIComponent(symbol);
    if (!detail) return read<T>(`brokers/index/${safeSymbol}.json`);
    if (detail === "sessions" || detail === "episodes") return read<T>(`brokers/${detail}/${detail === "sessions" ? `${safeSymbol}/` : ""}${encodeURIComponent(identifier)}.json`);
    if (detail === "history") {
      type Day = {quality: string; rows: Record<string, Pick<BrokerHistoryPoint, "bval" | "sval" | "blot" | "slot" | "bfreq" | "sfreq" | "nval" | "nlot" | "net_role">>};
      const history = await read<Record<string, Day>>(`brokers/history/${safeSymbol}.json`);
      const through = url.searchParams.get("through") ?? "";
      if (!Object.hasOwn(history, through)) throw new Error("Broker history cutoff is unavailable.");
      const available = Object.keys(history).sort().filter(day => day <= through);
      if (!available.some(day => Object.hasOwn(history[day].rows, identifier))) throw new Error("Broker code has not been returned by this cutoff.");
      const dates = available.slice(-20);

      const series: BrokerHistoryPoint[] = dates.map(date => {
        const session = history[date]; const row = session.rows[identifier];
        return {date, observation: row ? "RETURNED" : Object.keys(session.rows).length ? "NOT_RETURNED" : "BROKER_DATA_MISSING", session_quality: session.quality, bval: row?.bval ?? null, sval: row?.sval ?? null, blot: row?.blot ?? null, slot: row?.slot ?? null, bfreq: row?.bfreq ?? null, sfreq: row?.sfreq ?? null, nval: row?.nval ?? null, nlot: row?.nlot ?? null, net_role: row?.net_role ?? null};
      });
      return {symbol, broker_code: identifier, through, window_sessions: dates.length, returned_in_window: dates.some(day => Object.hasOwn(history[day].rows, identifier)), series} as BrokerHistory as T;
    }
  }
  if (["manifest", "overview", "methodology", "reaction-validation"].includes(section)) return read<T>(`product/${section}.json`);
  throw new Error("This demo endpoint is unavailable.");
}
