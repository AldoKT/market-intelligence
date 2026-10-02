import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getContext } from "../lib/api";
import type { ContextPayload } from "../types";
import { ContextBadge } from "../components/ContextBadge";
import { formatNumber, formatPercentRatio } from "../lib/format";

export function ContextPage() {
  const { symbol = "" } = useParams();
  const [data, setData] = useState<ContextPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    getContext(symbol)
      .then((payload) => {
        if (alive) setData(payload);
      })
      .catch((err: Error) => {
        if (alive) setError(err.message);
      });

    return () => {
      alive = false;
    };
  }, [symbol]);

  if (error) {
    return (
      <div className="error-card workspace-page">
        <h2>Unable to load Context</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="workspace-page">
        <div className="skeleton skeleton-card" />
      </div>
    );
  }

  const current = data.current;
  const market = data.daily_market;

  return (
    <section className="workspace-page">
      <section className="context-top-grid">
        <div className="card context-hero-card">
          <div className="section-heading">
            <div>
              <div className="eyebrow">Context Specificity</div>
              <h2>
                {current.specificity_score == null
                  ? "Not applicable"
                  : `${formatNumber(
                      current.specificity_score,
                      0
                    )}/100`}
              </h2>
            </div>
            <ContextBadge scope={current.scope} />
          </div>

          <p className="context-interpretation">
            {current.interpretation}
          </p>

          <div className="context-bars">
            <ContextBar
              label="Market activity percentile"
              value={current.market_activity_percentile}
            />
            <ContextBar
              label="Market activity breadth"
              value={current.market_activity_breadth}
            />
            <ContextBar
              label="Peer activity percentile"
              value={current.peer_activity_percentile}
            />
            <ContextBar
              label="Peer activity breadth"
              value={current.peer_activity_breadth}
            />
          </div>
        </div>

        <aside className="card peer-context-card">
          <div className="eyebrow">Peer Context</div>
          <h3>{data.identity.peer_group ?? "Unmapped group"}</h3>

          <div className="peer-context-stats">
            <ContextStat
              label="Peers observed"
              value={String(current.peer_count)}
            />
            <ContextStat
              label="Peer quality"
              value={current.peer_context_quality ?? "—"}
            />
            <ContextStat
              label="Peer breadth"
              value={formatPercentRatio(
                current.peer_activity_breadth,
                1
              )}
            />
          </div>

          <p>
            Peer groups in this prototype are research groupings. They are
            not presented as authoritative exchange classifications.
          </p>
        </aside>
      </section>

      <section className="card market-context-card">
        <div className="section-heading">
          <div>
            <div className="eyebrow">Market Context</div>
            <h3>Same-session breadth</h3>
          </div>
        </div>

        <div className="market-context-grid">
          <MarketMetric
            label="Eligible Universe"
            value={
              market.market_eligible_count == null
                ? "—"
                : String(market.market_eligible_count)
            }
          />
          <MarketMetric
            label="Median Activity"
            value={formatNumber(
              market.market_activity_median as number | undefined,
              1
            )}
          />
          <MarketMetric
            label="75th Percentile"
            value={formatNumber(
              market.market_activity_p75 as number | undefined,
              1
            )}
          />
          <MarketMetric
            label="Activity Gate Breadth"
            value={formatPercentRatio(
              market.market_activity_breadth as number | undefined,
              1
            )}
          />
          <MarketMetric
            label="Market Spot Hits"
            value={
              market.market_spot_hit_count == null
                ? "—"
                : String(market.market_spot_hit_count)
            }
          />
          <MarketMetric
            label="Spot Hit Breadth"
            value={formatPercentRatio(
              market.market_spot_hit_breadth as number | undefined,
              1
            )}
          />
        </div>
      </section>

      <section className="context-placeholder-grid">
        <UnavailableCard
          title="Company Fundamentals"
          text="Not included in the current offline research payload. SIGNAL does not fabricate ROE, leverage, market cap, or beta."
        />
        <UnavailableCard
          title="Corporate Events"
          text="No corporate-action payload is bundled into this historical demo snapshot."
        />
        <UnavailableCard
          title="Relevant News"
          text="News evidence is intentionally omitted from this offline build unless source records are explicitly available."
        />
      </section>

      <section className="card context-notes-card">
        <div className="eyebrow">Key Context Notes</div>
        <ul>
          {data.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}

function ContextBar({
  label,
  value
}: {
  label: string;
  value: number | null;
}) {
  const pct = value == null ? 0 : Math.max(0, Math.min(100, value * 100));

  return (
    <div className="context-bar-row">
      <div>
        <span>{label}</span>
        <strong>{formatPercentRatio(value, 1)}</strong>
      </div>
      <div className="context-bar-track">
        <span style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ContextStat({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MarketMetric({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="market-metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function UnavailableCard({
  title,
  text
}: {
  title: string;
  text: string;
}) {
  return (
    <div className="card unavailable-card">
      <div className="unavailable-icon">○</div>
      <h3>{title}</h3>
      <p>{text}</p>
      <span>Source unavailable in current snapshot</span>
    </div>
  );
}
