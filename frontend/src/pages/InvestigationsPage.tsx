import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  getInvestigation,
  getInvestigations
} from "../lib/api";
import type {
  InvestigationDetail,
  InvestigationExplorerPayload,
  InvestigationListItem
} from "../types";
import { InvestigationTable } from "../components/InvestigationTable";
import { StatusBadge } from "../components/StatusBadge";
import { ContextBadge } from "../components/ContextBadge";
import { ConfidenceGauge } from "../components/ConfidenceGauge";
import { WatchlistButton } from "../components/WatchlistButton";
import {
  formatDate,
  formatNumber,
  formatPercentRatio
} from "../lib/format";

export function InvestigationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [data, setData] =
    useState<InvestigationExplorerPayload | null>(null);
  const [detail, setDetail] = useState<InvestigationDetail | null>(null);

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const q = searchParams.get("q") ?? "";
  const state = searchParams.get("state") ?? "";
  const peerGroup = searchParams.get("peer_group") ?? "";
  const contextScope = searchParams.get("context_scope") ?? "";
  const activeParam = searchParams.get("active") ?? "";
  const selectedFromUrl = searchParams.get("symbol");

  const active =
    activeParam === ""
      ? undefined
      : activeParam === "true";

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);

    getInvestigations({
      q: q || undefined,
      state: state || undefined,
      peer_group: peerGroup || undefined,
      context_scope: contextScope || undefined,
      active
    })
      .then((payload) => {
        if (!alive) return;
        setData(payload);

        if (
          !selectedFromUrl &&
          payload.items.length > 0
        ) {
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.set("symbol", payload.items[0].symbol);
            return next;
          });
        }
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
  }, [
    q,
    state,
    peerGroup,
    contextScope,
    activeParam,
    selectedFromUrl,
    setSearchParams
  ]);

  useEffect(() => {
    if (!selectedFromUrl) {
      setDetail(null);
      return;
    }

    let alive = true;
    setDetailLoading(true);

    getInvestigation(selectedFromUrl)
      .then((payload) => {
        if (alive) setDetail(payload);
      })
      .catch(() => {
        if (alive) setDetail(null);
      })
      .finally(() => {
        if (alive) setDetailLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [selectedFromUrl]);

  const filterOptions = useMemo(() => {
    return data?.filters ?? {
      state: [],
      peer_group: [],
      context_scope: []
    };
  }, [data]);

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);

      if (!value) {
        next.delete(key);
      } else {
        next.set(key, value);
      }

      if (key !== "symbol") {
        next.delete("symbol");
      }

      return next;
    });
  }

  function selectItem(item: InvestigationListItem) {
    setParam("symbol", item.symbol);
  }

  return (
    <>
      <section className="page-header investigations-header">
        <div>
          <div className="eyebrow magenta">
            Active Investigation Explorer
          </div>
          <h1>Investigations</h1>
          <p>
            Explore flagged behavior, lifecycle state, context, and
            evidence consistency without turning the result into a
            trading recommendation.
          </p>
        </div>

        {data && (
          <div className="as-of">
            <span>As of</span>
            <strong>{formatDate(data.as_of)}</strong>
            <small>{data.methodology_version}</small>
          </div>
        )}
      </section>

      <section className="filter-bar card">
        <div className="search-box">
          <span>⌕</span>
          <input
            value={q}
            onChange={(event) => setParam("q", event.target.value)}
            placeholder="Search ticker..."
            aria-label="Search ticker"
          />
        </div>

        <FilterSelect
          label="State"
          value={state}
          options={filterOptions.state}
          onChange={(value) => setParam("state", value)}
        />

        <FilterSelect
          label="Peer group"
          value={peerGroup}
          options={filterOptions.peer_group}
          onChange={(value) => setParam("peer_group", value)}
        />

        <FilterSelect
          label="Context"
          value={contextScope}
          options={filterOptions.context_scope}
          onChange={(value) => setParam("context_scope", value)}
        />

        <select
          className="filter-select"
          value={activeParam}
          onChange={(event) => setParam("active", event.target.value)}
        >
          <option value="">All lifecycle states</option>
          <option value="true">Active only</option>
          <option value="false">Inactive only</option>
        </select>

        <button
          className="clear-button"
          onClick={() => setSearchParams({})}
        >
          Clear
        </button>
      </section>

      {error ? (
        <div className="error-card">
          <h2>Unable to load investigations</h2>
          <p>{error}</p>
        </div>
      ) : (
        <section className="investigations-layout">
          <div className="card explorer-table-card">
            <div className="table-toolbar">
              <div>
                <div className="eyebrow">Investigation Universe</div>
                <strong>
                  {loading ? "Loading…" : `${data?.items.length ?? 0} results`}
                </strong>
              </div>
            </div>

            {loading ? (
              <div className="table-loading">
                <div className="skeleton skeleton-card" />
              </div>
            ) : (
              <InvestigationTable
                items={data?.items ?? []}
                selectedSymbol={selectedFromUrl}
                onSelect={selectItem}
              />
            )}
          </div>

          <aside className="card quick-preview">
            <div className="eyebrow">Quick Preview</div>

            {detailLoading ? (
              <div className="preview-loading">
                <div className="skeleton skeleton-number" />
                <div className="skeleton skeleton-line" />
                <div className="skeleton skeleton-card small-card" />
              </div>
            ) : detail ? (
              <Preview
                detail={detail}
                onOpen={() =>
                  navigate(
                    `/investigations/${encodeURIComponent(
                      detail.identity.symbol
                    )}/summary`
                  )
                }
              />
            ) : (
              <div className="empty-state compact-empty">
                <h3>Select an investigation</h3>
                <p>
                  Click a ticker row to inspect its current lifecycle
                  state and evidence.
                </p>
              </div>
            )}
          </aside>
        </section>
      )}
    </>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      <select
        className="filter-select"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option.replaceAll("_", " ")}
          </option>
        ))}
      </select>
    </label>
  );
}

function Preview({
  detail,
  onOpen
}: {
  detail: InvestigationDetail;
  onOpen: () => void;
}) {
  return (
    <>
      <div className="preview-title">
        <div>
          <h2>{detail.identity.symbol}</h2>
          <p>{detail.identity.peer_group ?? "Unmapped peer group"}</p>
        </div>

        <StatusBadge state={detail.state} />
      </div>

      <div className="preview-watchlist-row">
        <WatchlistButton symbol={detail.identity.symbol} />
      </div>

      <div className="preview-gauge">
        <ConfidenceGauge
          value={detail.confidence.evidence_confidence}
        />
      </div>

      <div className="divider" />

      <div className="preview-section">
        <span className="eyebrow">Hypothesis</span>
        <strong>{detail.hypothesis}</strong>
      </div>

      <div className="preview-section">
        <span className="eyebrow">Context</span>
        <ContextBadge scope={detail.context.scope} />
        <p>{detail.context.interpretation}</p>
      </div>

      <div className="preview-metric-grid">
        <PreviewMetric
          label="Compression"
          value={
            detail.metrics.compression_score == null
              ? "—"
              : `${formatNumber(
                  detail.metrics.compression_score,
                  0
                )}/100`
          }
        />
        <PreviewMetric
          label="Activity"
          value={
            detail.metrics.activity_score == null
              ? "—"
              : `${formatNumber(
                  detail.metrics.activity_score,
                  0
                )}/100`
          }
        />
        <PreviewMetric
          label="Rel. turnover"
          value={
            detail.metrics.relative_turnover == null
              ? "—"
              : `${formatNumber(
                  detail.metrics.relative_turnover,
                  2
                )}×`
          }
        />
        <PreviewMetric
          label="Foreign flow"
          value={formatPercentRatio(
            detail.metrics.foreign_net_to_turnover
          )}
        />
      </div>

      <div className="divider" />

      <div className="preview-section">
        <span className="eyebrow">Persistence</span>
        <div className="persistence-meter">
          {Array.from({ length: 5 }).map((_, index) => (
            <span
              key={index}
              className={
                index <
                detail.persistence.support_sessions_in_last_5
                  ? "persistence-segment active"
                  : "persistence-segment"
              }
            />
          ))}
        </div>
        <p>
          {detail.persistence.support_sessions_in_last_5}/5 recent
          sessions support the hypothesis;{" "}
          {detail.persistence.hard_hits_total_in_episode} hard hit(s)
          in the episode.
        </p>
      </div>

      <button className="primary-button preview-button" onClick={onOpen}>
        Open Full Workspace →
      </button>
    </>
  );
}

function PreviewMetric({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="preview-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
