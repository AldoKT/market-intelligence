import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getActivity } from "../lib/api";
import type { ActivityPayload, ActivityPoint } from "../types";
import { SimpleLineChart } from "../components/SimpleLineChart";
import { formatNumber } from "../lib/format";

type MetricKey =
  | "close"
  | "turnover"
  | "volume"
  | "transactions"
  | "avgTrade"
  | "activity";

interface MetricDef {
  label: string;
  actualKey?: keyof ActivityPoint;
  relativeKey?: keyof ActivityPoint;
  reference?: number;
  referenceLabel?: string;
  suffix?: string;
}

const METRICS: Record<MetricKey, MetricDef> = {
  close: {
    label: "Price",
    actualKey: "close"
  },
  transactions: {
    label: "Transaction Count",
    actualKey: "transaction_count",
    relativeKey: "relative_transaction_count",
    reference: 1.2,
    referenceLabel: "1.20× baseline"
  },
  volume: {
    label: "Volume",
    actualKey: "volume",
    relativeKey: "relative_volume",
    reference: 1.2,
    referenceLabel: "1.20× baseline"
  },
  turnover: {
    label: "Turnover",
    actualKey: "turnover_idr",
    relativeKey: "relative_turnover",
    reference: 1.2,
    referenceLabel: "1.20× baseline"
  },
  avgTrade: {
    label: "Avg Trade Value",
    actualKey: "avg_trade_value_idr",
    relativeKey: "relative_avg_trade_value",
    reference: 1.2,
    referenceLabel: "1.20× baseline"
  },
  activity: {
    label: "Activity Score",
    actualKey: "activity_score",
    reference: 50,
    referenceLabel: "Hard activity gate"
  }
};

export function ActivityPage() {
  const { symbol = "" } = useParams();
  const [data, setData] = useState<ActivityPayload | null>(null);
  const [metric, setMetric] = useState<MetricKey>("turnover");
  const [windowSize, setWindowSize] = useState(20);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);

    getActivity(symbol)
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

  const resolved = useMemo(() => {
    if (!data) return null;

    const definition = METRICS[metric];
    const recent = data.series.slice(-windowSize);

    let key = definition.actualKey;
    let mode: "actual" | "relative" = "actual";

    const hasActual =
      key &&
      recent.some(
        (point) =>
          typeof point[key as keyof ActivityPoint] === "number"
      );

    if (!hasActual && definition.relativeKey) {
      key = definition.relativeKey;
      mode = "relative";
    }

    if (!key) return null;

    return {
      definition,
      mode,
      points: recent.map((point) => ({
        x: point.date,
        y:
          typeof point[key as keyof ActivityPoint] === "number"
            ? (point[key as keyof ActivityPoint] as number)
            : null,
        flag: point.spot_hit
      }))
    };
  }, [data, metric, windowSize]);

  if (error) {
    return (
      <div className="error-card workspace-page">
        <h2>Unable to load Market Activity</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (!data || !resolved) {
    return (
      <div className="workspace-page">
        <div className="skeleton skeleton-card" />
      </div>
    );
  }

  const current = data.current;

  return (
    <section className="workspace-page">
      <div className="card activity-main-card">
        <div className="activity-toolbar">
          <div>
            <div className="eyebrow">Market Activity</div>
            <h2>{resolved.definition.label}</h2>
            <p>
              Trading evidence only — narrative and lifecycle interpretation
              are intentionally kept on other pages.
            </p>
          </div>

          <div className="activity-controls">
            <div className="segmented-control">
              {(Object.keys(METRICS) as MetricKey[]).map((key) => (
                <button
                  key={key}
                  className={metric === key ? "active" : ""}
                  onClick={() => setMetric(key)}
                >
                  {METRICS[key].label}
                </button>
              ))}
            </div>

            <div className="window-control">
              {[5, 20, 60].map((size) => (
                <button
                  key={size}
                  className={windowSize === size ? "active" : ""}
                  onClick={() => setWindowSize(size)}
                >
                  {size}D
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="chart-mode-row">
          <span
            className={
              resolved.mode === "actual"
                ? "data-mode-chip"
                : "data-mode-chip relative"
            }
          >
            {resolved.mode === "actual"
              ? "Actual series"
              : "Relative-to-baseline series"}
          </span>

          {resolved.mode === "relative" && (
            <small>
              Actual cached raw series is not present in this demo payload.
            </small>
          )}
        </div>

        <SimpleLineChart
          points={resolved.points}
          height={330}
          reference={
            resolved.mode === "relative"
              ? resolved.definition.reference
              : metric === "activity"
              ? resolved.definition.reference
              : undefined
          }
          referenceLabel={resolved.definition.referenceLabel}
          suffix={resolved.mode === "relative" ? "×" : ""}
        />

        <div className="chart-legend-row">
          <span>
            <i className="legend-line" /> metric series
          </span>
          <span>
            <i className="legend-dot-flag" /> hard Spot hit
          </span>
          {resolved.mode === "relative" &&
            resolved.definition.reference !== undefined && (
              <span>
                <i className="legend-dash" /> threshold reference
              </span>
            )}
        </div>
      </div>

      <section className="activity-lower-grid">
        <div className="card activity-snapshot-card">
          <div className="section-heading">
            <div>
              <div className="eyebrow">Session Snapshot</div>
              <h3>Current observation</h3>
            </div>
          </div>

          <div className="snapshot-detail-grid">
            <ActivityMetric
              label="Close"
              value={formatNumber(current.close, 2)}
            />
            <ActivityMetric
              label="Compression Score"
              value={
                current.compression_score == null
                  ? "—"
                  : `${formatNumber(current.compression_score, 1)}/100`
              }
            />
            <ActivityMetric
              label="Activity Score"
              value={
                current.activity_score == null
                  ? "—"
                  : `${formatNumber(current.activity_score, 1)}/100`
              }
            />
            <ActivityMetric
              label="Relative Turnover"
              value={
                current.relative_turnover == null
                  ? "—"
                  : `${formatNumber(current.relative_turnover, 2)}×`
              }
            />
            <ActivityMetric
              label="Relative Volume"
              value={
                current.relative_volume == null
                  ? "—"
                  : `${formatNumber(current.relative_volume, 2)}×`
              }
            />
            <ActivityMetric
              label="Relative Transactions"
              value={
                current.relative_transaction_count == null
                  ? "—"
                  : `${formatNumber(
                      current.relative_transaction_count,
                      2
                    )}×`
              }
            />
          </div>
        </div>

        <div className="card cross-metric-card">
          <div className="eyebrow">Cross-Metric Comparison</div>
          <h3>Relative activity</h3>

          <MetricBar
            label="Turnover"
            value={current.relative_turnover}
          />
          <MetricBar
            label="Volume"
            value={current.relative_volume}
          />
          <MetricBar
            label="Transactions"
            value={current.relative_transaction_count}
          />
          <MetricBar
            label="Avg Trade Value"
            value={current.relative_avg_trade_value}
          />

          <p className="card-footnote">{data.guardrail}</p>
        </div>
      </section>
    </section>
  );
}

function ActivityMetric({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="activity-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MetricBar({
  label,
  value
}: {
  label: string;
  value: number | null;
}) {
  const width =
    value == null ? 0 : Math.min(100, Math.max(0, (value / 3) * 100));

  return (
    <div className="metric-bar-row">
      <div>
        <span>{label}</span>
        <strong>{value == null ? "—" : `${formatNumber(value, 2)}×`}</strong>
      </div>

      <div className="metric-bar-track">
        <span style={{ width: `${width}%` }} />
        <i style={{ left: `${(1.2 / 3) * 100}%` }} />
      </div>
    </div>
  );
}
