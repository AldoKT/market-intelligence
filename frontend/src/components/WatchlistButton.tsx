import { useWatchlist } from "../lib/watchlist";

export function WatchlistButton({
  symbol,
  compact = false
}: {
  symbol: string;
  compact?: boolean;
}) {
  const watchlist = useWatchlist();
  const active = watchlist.has(symbol);

  return (
    <button
      className={
        compact
          ? `watchlist-icon-button ${active ? "active" : ""}`
          : `watchlist-button ${active ? "active" : ""}`
      }
      onClick={() => watchlist.toggle(symbol)}
      title={active ? "Remove from watchlist" : "Add to watchlist"}
      aria-label={active ? "Remove from watchlist" : "Add to watchlist"}
    >
      <span>{active ? "★" : "☆"}</span>
      {!compact && (
        <span>{active ? "Watching" : "Add to Watchlist"}</span>
      )}
    </button>
  );
}
