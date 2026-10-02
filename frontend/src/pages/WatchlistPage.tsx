import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getInvestigations } from "../lib/api";
import type {
  InvestigationExplorerPayload,
  InvestigationListItem
} from "../types";
import { useWatchlist } from "../lib/watchlist";
import { InvestigationTable } from "../components/InvestigationTable";
import { WatchlistButton } from "../components/WatchlistButton";
import { KpiCard } from "../components/KpiCard";

export function WatchlistPage() {
  const [data, setData] =
    useState<InvestigationExplorerPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const watchlist = useWatchlist();
  const navigate = useNavigate();

  useEffect(() => {
    let alive = true;

    getInvestigations()
      .then((payload) => {
        if (alive) setData(payload);
      })
      .catch((err: Error) => {
        if (alive) setError(err.message);
      });

    return () => {
      alive = false;
    };
  }, []);

  const items = useMemo(() => {
    if (!data) return [];

    return data.items.filter((item) =>
      watchlist.symbols.includes(item.symbol)
    );
  }, [data, watchlist.symbols]);

  const active = items.filter((item) => item.active);
  const established = items.filter(
    (item) => item.state === "ESTABLISHED"
  );
  const changing = items.filter(
    (item) =>
      item.state === "EMERGING" ||
      item.state === "WEAKENING"
  );

  if (error) {
    return (
      <div className="error-card">
        <h2>Unable to load Watchlist</h2>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <>
      <section className="page-header">
        <div>
          <div className="eyebrow magenta">My Watchlist</div>
          <h1>Stocks you chose to monitor</h1>
          <p>
            Watchlist state is stored locally in this browser. It does not
            alter SIGNAL's detection methodology or API data.
          </p>
        </div>
      </section>

      <section className="kpi-grid">
        <KpiCard
          label="Watched Stocks"
          value={items.length}
          helper="Stored locally"
        />
        <KpiCard
          label="Active Investigations"
          value={active.length}
          helper="Current snapshot"
        />
        <KpiCard
          label="Established"
          value={established.length}
          helper="Persistent evidence"
        />
        <KpiCard
          label="State Changes"
          value={changing.length}
          helper="Emerging or weakening"
        />
      </section>

      {items.length ? (
        <section className="watchlist-layout">
          <div className="card table-card">
            <div className="section-heading table-heading">
              <div>
                <div className="eyebrow">Watchlist Monitor</div>
                <h3>Current investigation state</h3>
              </div>
            </div>

            <InvestigationTable
              items={items}
              onSelect={(item) =>
                navigate(`/investigations/${item.symbol}/summary`)
              }
            />
          </div>

          <aside className="card watchlist-actions-card">
            <div className="eyebrow">Manage</div>
            <h3>{watchlist.symbols.length} ticker(s)</h3>
            <div className="watchlist-symbol-list">
              {watchlist.symbols.map((symbol) => (
                <div key={symbol}>
                  <strong>{symbol}</strong>
                  <WatchlistButton symbol={symbol} compact />
                </div>
              ))}
            </div>

            <button
              className="secondary-button full-width"
              onClick={() => navigate("/investigations")}
            >
              Browse Investigations
            </button>
          </aside>
        </section>
      ) : (
        <section className="card watchlist-empty">
          <div className="empty-state">
            <div className="empty-icon">☆</div>
            <h3>Your watchlist is empty</h3>
            <p>
              Open an investigation and choose “Add to Watchlist”.
              Watchlist membership is only a viewing preference.
            </p>
            <button
              className="primary-button"
              onClick={() => navigate("/investigations")}
            >
              Browse Investigations
            </button>
          </div>
        </section>
      )}
    </>
  );
}
