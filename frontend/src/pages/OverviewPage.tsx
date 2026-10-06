import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getActivity, getInvestigation, getOverview } from "../lib/api";
import type {
  ActivityPayload,
  InvestigationDetail,
  InvestigationListItem,
  OverviewPayload
} from "../types";
import { formatDate, formatNumber } from "../lib/format";
import { companyName } from "../lib/companies";
import { withLatestPrice } from "../lib/pilot";

type DetailMap = Record<string, InvestigationDetail | null>;

export function OverviewPage() {
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [spotActivity, setSpotActivity] = useState<ActivityPayload | null>(null);
  const [details, setDetails] = useState<DetailMap>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let alive = true;

    getOverview()
      .then(async (payload) => {
        if (!alive) return;
        setData(payload);

        const symbols = Array.from(
          new Set([
            ...(payload.spotlight ? [payload.spotlight.symbol] : []),
            ...payload.active_investigations.slice(0, 5).map((item) => item.symbol)
          ])
        );

        const [detailEntries, activity] = await Promise.all([
          Promise.all(
            symbols.map(async (symbol) => {
              const detail = await getInvestigation(symbol).catch(() => null);
              return [symbol, detail] as const;
            })
          ),
          payload.spotlight
            ? getActivity(payload.spotlight.symbol).catch(() => null)
            : Promise.resolve(null)
        ]);

        if (!alive) return;
        setDetails(Object.fromEntries(detailEntries));
        setSpotActivity(activity);
        if(activity&&payload.spotlight){const spotlight=withLatestPrice(payload.spotlight,activity);setData({...payload,spotlight,active_investigations:payload.active_investigations.map(item=>item.symbol===spotlight.symbol?spotlight:item)});}
      })
      .catch((err: Error) => alive && setError(err.message))
      .finally(() => alive && setLoading(false));

    return () => {
      alive = false;
    };
  }, []);

  const kpis = useMemo(() => {
    if (!data) {
      return { detected: 0, strong: 0, persisting: 0, newToday: 0 };
    }

    return {
      detected: data.kpis.active_investigations,
      strong: data.active_investigations.filter(
        (item) => (item.evidence_confidence ?? 0) >= 80
      ).length,
      persisting: data.active_investigations.filter(
        (item) => item.persistence_hits >= 2
      ).length,
      newToday: data.active_investigations.filter(
        (item) => item.opened_at === data.as_of
      ).length
    };
  }, [data]);

  if (loading) return <OverviewSkeleton />;

  if (error || !data) {
    return (
      <div className="error-card">
        <h2>Unable to load SIGNAL Overview</h2>
        <p>{error ?? "Unknown API error."}</p>
      </div>
    );
  }

  const pilot = data.kpis.pilot_symbols != null;
  const latestPrice = spotActivity?.series.at(-1)?.close;
  const spotlight = data.spotlight;
  const spotDetail = spotlight ? details[spotlight.symbol] : null;
  const pricePoints = spotActivity?.series.slice(-30) ?? [];

  return (
    <section className="overview-pdf-page">
      <header className="overview-pdf-heading">
        <div>
          <div className="overview-pdf-date">{formatLongDate(data.as_of)}</div>
          <h1>{stripTrailingPeriod(data.headline)}.</h1>
        </div>

        <div className="overview-market-meta" aria-label="Snapshot metadata">
          <span>Historical snapshot · after market close</span>
          <strong>
            As of {formatDate(data.as_of)}
            <em>{data.methodology_version}</em>
          </strong>
        </div>
      </header>

      <section className="overview-pdf-main-grid">
        <article className="overview-spotlight-card">
          {spotlight ? (
            <>
              <div className="overview-spotlight-copy">
                <span className="overview-spotlight-badge">
                  <StarIcon />
                  Spotlight Investigation
                </span>

                <h2>{spotlight.symbol}</h2>

                <div className="overview-company-row">
                  <strong>
                    {companyName(spotlight.symbol, spotDetail?.identity.company_name)}
                  </strong>
                  <span>{humanGroup(spotlight.peer_group)}</span>
                  <span>{humanState(spotlight.state)}</span>
                </div>

                <p>
                  {spotDetail?.narrative_5w1h.why ??
                    spotDetail?.narrative_5w1h.what ??
                    "SIGNAL is tracking unusual market activity while the price range remains compressed."}
                </p>

                <button
                  className="overview-open-button"
                  onClick={() =>
                    navigate(`/investigations/${spotlight.symbol}/summary`)
                  }
                >
                  Open Investigation
                  <ArrowRightIcon />
                </button>
              </div>

              <div className="overview-spotlight-visual">
                <div className="overview-visual-top">
                  <OverviewConfidenceGauge
                    value={spotlight.evidence_confidence}
                  />

                  <div className="overview-last-price">
                    <span>Last Price (IDR)</span>
                    <strong>
                      {(spotlight.close ?? latestPrice) == null
                        ? "—"
                        : formatNumber((spotlight.close ?? latestPrice)!, 0)}
                    </strong>
                    <em className={changeClass(spotlight.daily_change_pct)}>
                      {spotlight.daily_change_pct == null
                        ? "1D change unavailable"
                        : `${spotlight.daily_change_pct >= 0 ? "▲ +" : "▼ "}${formatNumber(
                            spotlight.daily_change_pct,
                            2
                          )}%`}
                    </em>
                  </div>
                </div>

                <OverviewPriceChart
                  points={pricePoints.map((point) => ({
                    date: point.date,
                    value: point.close
                  }))}
                  current={spotlight.close}
                />
              </div>
            </>
          ) : (
            <div className="overview-empty-spotlight">
              <span className="overview-spotlight-badge">
                <StarIcon />
                Spotlight Investigation
              </span>
              <h2>No active investigation</h2>
              <p>
                This snapshot legitimately contains no active lifecycle state.
              </p>
            </div>
          )}
        </article>

        <aside className="overview-kpi-grid">
          <OverviewKpi
            icon={<BarsIcon />}
            label={<>Detected<br />Investigations</>}
            value={kpis.detected}
            helper="current snapshot"
            tone="positive"
          />
          <OverviewKpi
            icon={<BoltIcon />}
            label={pilot?"Saham pilot":<>Strong Signals<br /><span>(≥ 80)</span></>}
            value={pilot?data.kpis.pilot_symbols!:kpis.strong}
            helper={pilot?"ANTM · INCO · BBCA":"high confidence"}
            tone="positive"
          />
          <OverviewKpi
            icon={<ClockIcon />}
            label={pilot?"Episode teramati":<>Persisting<br />Investigations</>}
            value={pilot?data.kpis.observed_episodes??0:kpis.persisting}
            helper={pilot?"selama periode analisis":"≥ 2 support sessions"}
            tone="neutral"
          />
          <OverviewKpi
            icon={<PlusIcon />}
            label={pilot?"Belum dapat dinilai":"New Today"}
            value={pilot?data.kpis.withheld_analysis_sessions??0:kpis.newToday}
            helper={pilot?"sesi saham; bukan nol sinyal":`opened ${formatDate(data.as_of)}`}
            tone={pilot?"neutral":"positive"}
          />
        </aside>
      </section>

      <section className="overview-latest-card">
        <div className="overview-latest-head">
          <h3>Latest Investigations</h3>
          <button onClick={() => navigate("/investigations")}>
            View all investigations
            <ArrowRightIcon />
          </button>
        </div>

        <OverviewInvestigationsTable
          items={data.active_investigations.slice(0, 5)}
          details={details}
          asOf={data.as_of}
          onOpen={(symbol) =>
            navigate(`/investigations/${symbol}/summary`)
          }
        />
      </section>
    </section>
  );
}

function OverviewConfidenceGauge({ value }: { value: number | null }) {
  const safe = Math.max(0, Math.min(100, value ?? 0));
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const progress = (safe / 100) * circumference;

  return (
    <div className="overview-confidence-block">
      <div className="overview-confidence-title">
        Signal Confidence
        <span title="Evidence consistency score; not a return probability.">i</span>
      </div>
      <div className="overview-confidence-ring">
        <svg viewBox="0 0 132 132" aria-hidden="true">
          <circle
            cx="66"
            cy="66"
            r={radius}
            className="overview-confidence-track"
          />
          <circle
            cx="66"
            cy="66"
            r={radius}
            className="overview-confidence-progress"
            strokeDasharray={`${progress} ${circumference - progress}`}
          />
        </svg>
        <div className="overview-confidence-number">
          <strong>{value == null ? "—" : formatNumber(value, 0)}</strong>
          <span>/100</span>
        </div>
      </div>
    </div>
  );
}

function OverviewPriceChart({
  points,
  current
}: {
  points: Array<{ date: string; value: number | null }>;
  current: number | null | undefined;
}) {
  const usable = points.filter(
    (point): point is { date: string; value: number } =>
      typeof point.value === "number" && Number.isFinite(point.value)
  );

  if (usable.length < 2) {
    return (
      <div className="overview-price-chart overview-price-chart-empty">
        Price history unavailable
      </div>
    );
  }

  const width = 560;
  const height = 176;
  const left = 48;
  const right = 18;
  const top = 10;
  const bottom = 30;
  const chartW = width - left - right;
  const chartH = height - top - bottom;
  const rawMin = Math.min(...usable.map((point) => point.value));
  const rawMax = Math.max(...usable.map((point) => point.value));
  const pad = Math.max((rawMax - rawMin) * 0.14, Math.abs(rawMax) * 0.01, 1);
  const min = rawMin - pad;
  const max = rawMax + pad;
  const span = max - min || 1;

  const xy = usable.map((point, index) => ({
    ...point,
    x: left + (index / Math.max(1, usable.length - 1)) * chartW,
    y: top + ((max - point.value) / span) * chartH
  }));

  const linePath = xy
    .map((point, index) =>
      `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.y.toFixed(2)}`
    )
    .join(" ");
  const areaPath = `${linePath} L${xy[xy.length - 1].x.toFixed(2)},${(
    top + chartH
  ).toFixed(2)} L${xy[0].x.toFixed(2)},${(top + chartH).toFixed(2)} Z`;

  const yTicks = [0, 1, 2, 3].map((i) => {
    const value = max - (i / 3) * span;
    const y = top + (i / 3) * chartH;
    return { value, y };
  });

  const xIndexes = Array.from(
    new Set([0, Math.round((usable.length - 1) * 0.25), Math.round((usable.length - 1) * 0.5), Math.round((usable.length - 1) * 0.75), usable.length - 1])
  );

  const finalPoint = xy[xy.length - 1];

  return (
    <svg
      className="overview-price-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Spotlight price history"
    >
      <defs>
        <linearGradient id="overviewPriceFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#ee1978" stopOpacity="0.26" />
          <stop offset="100%" stopColor="#ee1978" stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {yTicks.map((tick, index) => (
        <g key={index}>
          <line
            x1={left}
            x2={width - right}
            y1={tick.y}
            y2={tick.y}
            className="overview-chart-gridline"
          />
          <text
            x={left - 10}
            y={tick.y + 4}
            textAnchor="end"
            className="overview-chart-axis"
          >
            {formatCompactNumber(tick.value)}
          </text>
        </g>
      ))}

      <path d={areaPath} fill="url(#overviewPriceFill)" />
      <path d={linePath} className="overview-chart-line" />

      {xIndexes.map((index) => {
        const point = xy[index];
        return (
          <text
            key={index}
            x={point.x}
            y={height - 8}
            textAnchor={
              index === 0 ? "start" : index === usable.length - 1 ? "end" : "middle"
            }
            className="overview-chart-axis"
          >
            {formatShortDate(point.date)}
          </text>
        );
      })}

      <circle
        cx={finalPoint.x}
        cy={finalPoint.y}
        r="5"
        className="overview-chart-end-dot"
      />

      <g
        transform={`translate(${Math.max(left, finalPoint.x - 22)},${Math.max(
          2,
          finalPoint.y - 34
        )})`}
      >
        <rect width="54" height="24" rx="6" className="overview-chart-price-tag" />
        <text x="27" y="16" textAnchor="middle" className="overview-chart-price-text">
          {current == null ? formatCompactNumber(finalPoint.value) : formatNumber(current, 0)}
        </text>
      </g>
    </svg>
  );
}

function OverviewKpi({
  icon,
  label,
  value,
  helper,
  tone
}: {
  icon: React.ReactNode;
  label: React.ReactNode;
  value: number;
  helper: string;
  tone: "positive" | "neutral";
}) {
  return (
    <article className="overview-kpi-card">
      <div className="overview-kpi-top">
        <span className="overview-kpi-icon">{icon}</span>
        <div className="overview-kpi-label">{label}</div>
      </div>
      <strong>{value}</strong>
      <small className={tone === "positive" ? "overview-kpi-positive" : "overview-kpi-neutral"}>
        {tone === "positive" ? "▲" : "→"} {helper}
      </small>
    </article>
  );
}

function OverviewInvestigationsTable({
  items,
  details,
  asOf,
  onOpen
}: {
  items: InvestigationListItem[];
  details: DetailMap;
  asOf: string;
  onOpen: (symbol: string) => void;
}) {
  return (
    <div className="overview-table-wrap">
      <table className="overview-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Ticker</th>
            <th>Company</th>
            <th>Signal Score <span>⌄</span></th>
            <th>Last Price (IDR)</th>
            <th>1D Change</th>
            <th>Key Insight</th>
            <th>Status</th>
            <th>Detected <span>⌄</span></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => {
            const detail = details[item.symbol];
            return (
              <tr key={item.symbol} onClick={() => onOpen(item.symbol)}>
                <td>{index + 1}</td>
                <td><strong className="overview-table-ticker">{item.symbol}</strong></td>
                <td>{companyName(item.symbol, detail?.identity.company_name)}</td>
                <td>
                  <span className="overview-score-pill">
                    {item.evidence_confidence == null
                      ? "—"
                      : formatNumber(item.evidence_confidence, 0)}
                  </span>
                </td>
                <td>{(item.close ?? detail?.metrics.close) == null ? "—" : formatNumber((item.close ?? detail?.metrics.close)!, 0)}</td>
                <td>
                  <span className={changeClass(item.daily_change_pct)}>
                    {item.daily_change_pct == null
                      ? "—"
                      : `${item.daily_change_pct >= 0 ? "+" : ""}${formatNumber(
                          item.daily_change_pct,
                          2
                        )}%`}
                  </span>
                </td>
                <td>
                  <span className="overview-table-insight">
                    {detail?.narrative_5w1h.what ??
                      "SIGNAL detected unusual market activity and opened an investigation."}
                  </span>
                </td>
                <td>
                  <OverviewStatusPill item={item} asOf={asOf} />
                </td>
                <td>{formatDate(item.opened_at ?? item.last_updated)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function OverviewStatusPill({
  item,
  asOf
}: {
  item: InvestigationListItem;
  asOf: string;
}) {
  if (item.opened_at === asOf) {
    return <span className="overview-status-pill overview-status-new">New Today</span>;
  }
  if (item.state === "WEAKENING") {
    return <span className="overview-status-pill overview-status-monitor">Monitoring</span>;
  }
  return <span className="overview-status-pill overview-status-persist">Persisting</span>;
}

function BarsIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3" y="12" width="3" height="7" rx="1" />
      <rect x="9" y="8" width="3" height="11" rx="1" />
      <rect x="15" y="4" width="3" height="15" rx="1" />
    </svg>
  );
}

function BoltIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M13.4 2 5.7 13h5.1L9.7 22 18.3 9.5h-5.2L13.4 2Z" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M12 7v5l3 2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m12 3 2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7L6.8 19l1-5.8-4.2-4.1 5.8-.8L12 3Z" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h13M14 7l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function stripTrailingPeriod(value: string) {
  return value.replace(/[.\s]+$/, "");
}

function humanGroup(value: string | null) {
  if (!value) return "Unmapped group";
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function humanState(value: string) {
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function changeClass(value?: number | null) {
  if (value == null || value === 0) return "v2-change-neutral";
  return value > 0 ? "v2-change-positive" : "v2-change-negative";
}

function formatLongDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric"
  }).format(date);
}

function formatShortDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short"
  }).format(date);
}

function formatCompactNumber(value: number) {
  const magnitude = Math.abs(value);
  if (magnitude >= 1000) return formatNumber(value, 0);
  if (magnitude >= 100) return formatNumber(value, 0);
  return formatNumber(value, 1);
}

function OverviewSkeleton() {
  return (
    <div className="overview-pdf-page">
      <div className="skeleton skeleton-header" />
      <div className="overview-pdf-main-grid">
        <div className="card skeleton-card" />
        <div className="card skeleton-card" />
      </div>
    </div>
  );
}
