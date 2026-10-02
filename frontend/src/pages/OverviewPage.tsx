import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getOverview } from "../lib/api";
import type { OverviewPayload } from "../types";
import { KpiCard } from "../components/KpiCard";
import { ConfidenceGauge } from "../components/ConfidenceGauge";
import { InvestigationTable } from "../components/InvestigationTable";
import { StatusBadge } from "../components/StatusBadge";
import { ContextBadge } from "../components/ContextBadge";
import { formatDate, formatNumber } from "../lib/format";

export function OverviewPage() {
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let alive = true;

    getOverview()
      .then((payload) => {
        if (alive) setData(payload);
      })
      .catch((err: Error) => {
        if (alive) setError(err.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  const contextBreakdown = useMemo(() => {
    if (!data) return [];

    const counts = new Map<string, number>();

    data.active_investigations.forEach((item) => {
      const key = item.context_scope ?? "NO_CONTEXT";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });

    return Array.from(counts.entries())
      .map(([scope, count]) => ({ scope, count }))
      .sort((a, b) => b.count - a.count);
  }, [data]);

  if (loading) {
    return <OverviewSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="error-card">
        <h2>Unable to load SIGNAL Overview</h2>
        <p>{error ?? "Unknown API error."}</p>
        <code>Check that FastAPI is running on port 8000.</code>
      </div>
    );
  }

  const spotlight = data.spotlight;

  return (
    <>
      <section className="page-header">
        <div>
          <div className="eyebrow magenta">Post-market investigation engine</div>
          <h1>{data.headline}</h1>
          <p>
            Structured evidence from price compression, abnormal activity,
            persistence, participation, and market context.
          </p>
        </div>

        <div className="as-of">
          <span>As of</span>
          <strong>{formatDate(data.as_of)}</strong>
          <small>{data.methodology_version}</small>
        </div>
      </section>

      <section className="kpi-grid">
        <KpiCard
          label="Active Investigations"
          value={data.kpis.active_investigations}
          helper="Open lifecycle states"
        />
        <KpiCard
          label="Established"
          value={data.kpis.established}
          helper="Persistent evidence"
        />
        <KpiCard
          label="Developing"
          value={data.kpis.developing}
          helper="Evidence still building"
        />
        <KpiCard
          label="Weakening"
          value={data.kpis.weakening}
          helper="Continuation under review"
        />
      </section>

      <section className="overview-grid">
        <div className="card spotlight-card">
          <div className="section-heading">
            <div>
              <div className="eyebrow">Spotlight Investigation</div>
              <h2>
                {spotlight ? spotlight.symbol : "No active investigation"}
              </h2>
            </div>

            {spotlight && (
              <StatusBadge state={spotlight.state} />
            )}
          </div>

          {spotlight ? (
            <>
              <div className="spotlight-body">
                <ConfidenceGauge
                  value={spotlight.evidence_confidence}
                />

                <div className="spotlight-metrics">
                  <Metric
                    label="Context"
                    value={
                      <ContextBadge scope={spotlight.context_scope} />
                    }
                  />
                  <Metric
                    label="Relative Turnover"
                    value={
                      spotlight.relative_turnover == null
                        ? "—"
                        : `${formatNumber(
                            spotlight.relative_turnover,
                            2
                          )}×`
                    }
                  />
                  <Metric
                    label="5D Price Range"
                    value={
                      spotlight.current_5d_range_pct == null
                        ? "—"
                        : `${formatNumber(
                            spotlight.current_5d_range_pct,
                            2
                          )}%`
                    }
                  />
                  <Metric
                    label="Persistence"
                    value={`${spotlight.persistence_hits}/${spotlight.persistence_window} sessions`}
                  />
                </div>
              </div>

              <div className="spotlight-summary">
                <strong>Sideways Accumulation Watch</strong>
                <p>
                  SIGNAL is tracking whether abnormal trading activity
                  continues while the price range remains compressed.
                </p>
              </div>

              <button
                className="primary-button"
                onClick={() =>
                  navigate(
                    `/investigations/${encodeURIComponent(
                      spotlight.symbol
                    )}/summary`
                  )
                }
              >
                Open Investigation
                <span>→</span>
              </button>
            </>
          ) : (
            <div className="empty-state compact-empty">
              <p>
                The current snapshot contains no active investigation.
                Historical snapshots can be used to inspect prior episodes.
              </p>
            </div>
          )}
        </div>

        <aside className="card pulse-card">
          <div className="section-heading">
            <div>
              <div className="eyebrow">Market Pulse</div>
              <h3>Context mix</h3>
            </div>
          </div>

          <div className="pulse-list">
            {contextBreakdown.length ? (
              contextBreakdown.map((item) => (
                <div className="pulse-row" key={item.scope}>
                  <ContextBadge scope={item.scope} />
                  <strong>{item.count}</strong>
                </div>
              ))
            ) : (
              <p className="muted">
                No active investigation context to summarize.
              </p>
            )}
          </div>

          <div className="divider" />

          <div className="eyebrow">Recent changes</div>
          <div className="recent-list">
            {data.recent_changes.slice(0, 5).map((change) => (
              <div className="recent-item" key={`${change.symbol}-${change.state}`}>
                <div>
                  <strong>{change.symbol}</strong>
                  <span>{change.state.replaceAll("_", " ")}</span>
                </div>
                <small>{formatDate(change.date)}</small>
              </div>
            ))}
          </div>
        </aside>
      </section>

      <section className="card table-card">
        <div className="section-heading table-heading">
          <div>
            <div className="eyebrow">Active Investigations</div>
            <h3>What needs attention</h3>
          </div>

          <button
            className="secondary-button"
            onClick={() => navigate("/investigations")}
          >
            View all
          </button>
        </div>

        <InvestigationTable
          compact
          items={data.active_investigations.slice(0, 8)}
          onSelect={(item) =>
            navigate(
              `/investigations/${encodeURIComponent(item.symbol)}/summary`
            )
          }
        />
      </section>
    </>
  );
}

function Metric({
  label,
  value
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="metric-block">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div>
      <div className="skeleton skeleton-header" />
      <div className="kpi-grid">
        {Array.from({ length: 4 }).map((_, index) => (
          <div className="card kpi-card" key={index}>
            <div className="skeleton skeleton-line small" />
            <div className="skeleton skeleton-number" />
          </div>
        ))}
      </div>
      <div className="overview-grid">
        <div className="card skeleton-card" />
        <div className="card skeleton-card" />
      </div>
    </div>
  );
}
