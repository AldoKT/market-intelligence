import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getReactionValidation, getSummary } from "../lib/api";
import type { ReactionValidationPayload, SummaryPayload } from "../types";
import { ConfidenceGauge } from "../components/ConfidenceGauge";
import { EvidenceCard } from "../components/EvidenceCard";
import { ContextBadge } from "../components/ContextBadge";
import { formatNumber, formatPercentRatio } from "../lib/format";
import { HistoricalReactionProfile } from "../components/HistoricalReactionProfile";

export function SummaryPage() {
  const { symbol = "" } = useParams();
  const [data, setData] = useState<SummaryPayload | null>(null);
  const [reaction, setReaction] = useState<ReactionValidationPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);

    getSummary(symbol)
      .then((payload) => {
        if (alive) setData(payload);
      })
      .catch((err: Error) => {
        if (alive) setError(err.message);
      });

    getReactionValidation()
      .then((payload) => {
        if (alive) setReaction(payload);
      })
      .catch(() => {
        if (alive) setReaction(null);
      });

    return () => {
      alive = false;
    };
  }, [symbol]);

  if (error) {
    return <PageError title="Unable to load Summary" message={error} />;
  }

  if (!data) {
    return <WorkspaceLoading />;
  }

  const inv = data.investigation;

  return (
    <section className="workspace-page">
      <div className="workspace-main-grid">
        <div className="card investigation-report">
          <div className="section-heading">
            <div>
              <div className="eyebrow">Investigation Report</div>
              <h2>{inv.hypothesis}</h2>
            </div>
            <ContextBadge scope={inv.context.scope} />
          </div>

          <div className="report-core-grid">
            <ConfidenceGauge
              value={inv.confidence.evidence_confidence}
            />

            <div className="report-score-grid">
              <ScoreTile
                label="Compression"
                value={inv.metrics.compression_score}
                suffix="/100"
              />
              <ScoreTile
                label="Activity"
                value={inv.metrics.activity_score}
                suffix="/100"
              />
              <ScoreTile
                label="Persistence"
                value={inv.persistence.persistence_score}
                suffix="/100"
              />
              <ScoreTile
                label="Relative Turnover"
                value={inv.metrics.relative_turnover}
                suffix="×"
                digits={2}
              />
            </div>
          </div>

          <div className="report-hypothesis">
            <span className="eyebrow">What SIGNAL sees</span>
            <p>{inv.narrative_5w1h.what}</p>
            <small>{inv.narrative_5w1h.why}</small>
          </div>
        </div>

        <aside className="card monitor-card">
          <div className="eyebrow">What to Monitor Next</div>
          <h3>Continuation conditions</h3>

          <div className="monitor-list">
            {inv.look_ahead.map((condition) => (
              <div className="monitor-row" key={condition.condition_id}>
                <span
                  className={`condition-dot ${
                    condition.current_status === "MET"
                      ? "condition-met"
                      : condition.current_status === "NOT_MET"
                      ? "condition-not-met"
                      : ""
                  }`}
                />
                <div>
                  <strong>{condition.label}</strong>
                  <p>{condition.note}</p>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>

      <section className="snapshot-grid">
        <SnapshotCard
          label="Price Range"
          value={
            inv.metrics.current_5d_range_pct == null
              ? "—"
              : `${formatNumber(
                  inv.metrics.current_5d_range_pct,
                  2
                )}%`
          }
          helper={
            inv.metrics.baseline_5d_range_pct == null
              ? "Baseline unavailable"
              : `Baseline ${formatNumber(
                  inv.metrics.baseline_5d_range_pct,
                  2
                )}%`
          }
        />
        <SnapshotCard
          label="Relative Volume"
          value={
            inv.metrics.relative_volume == null
              ? "—"
              : `${formatNumber(inv.metrics.relative_volume, 2)}×`
          }
          helper="vs 20-session median"
        />
        <SnapshotCard
          label="Relative Transactions"
          value={
            inv.metrics.relative_transaction_count == null
              ? "—"
              : `${formatNumber(
                  inv.metrics.relative_transaction_count,
                  2
                )}×`
          }
          helper="vs 20-session median"
        />
        <SnapshotCard
          label="Foreign Net / Turnover"
          value={formatPercentRatio(
            inv.metrics.foreign_net_to_turnover,
            1
          )}
          helper="supporting context only"
        />
      </section>

      {reaction && (
        <HistoricalReactionProfile
          data={reaction}
          currentAsOf={data.as_of}
          respectPointInTime
        />
      )}

      <section className="card narrative-card">
        <div className="section-heading">
          <div>
            <div className="eyebrow">Narrative</div>
            <h3>5W + 1H</h3>
          </div>
        </div>

        <div className="narrative-grid">
          <NarrativeItem label="What" value={inv.narrative_5w1h.what} />
          <NarrativeItem label="Why" value={inv.narrative_5w1h.why} />
          <NarrativeItem label="When" value={inv.narrative_5w1h.when} />
          <NarrativeItem label="Where" value={inv.narrative_5w1h.where} />
          <NarrativeItem label="Who" value={inv.narrative_5w1h.who} />
          <NarrativeItem label="How" value={inv.narrative_5w1h.how} />
        </div>
      </section>

      <section className="evidence-section">
        <div className="section-heading evidence-heading">
          <div>
            <div className="eyebrow">Assess</div>
            <h3>Evidence map</h3>
          </div>
          <p>
            Supporting evidence and contradicting evidence are shown
            side-by-side. Neither is hidden.
          </p>
        </div>

        <div className="evidence-columns">
          <div>
            <h4 className="evidence-column-title support-title">
              Supporting ({inv.supporting_evidence.length})
            </h4>
            <div className="evidence-stack">
              {inv.supporting_evidence.map((item) => (
                <EvidenceCard key={item.evidence_id} evidence={item} />
              ))}
            </div>
          </div>

          <div>
            <h4 className="evidence-column-title contradict-title">
              Contradicting ({inv.contradicting_evidence.length})
            </h4>
            <div className="evidence-stack">
              {inv.contradicting_evidence.map((item) => (
                <EvidenceCard key={item.evidence_id} evidence={item} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="card guardrail-card">
        <div>
          <div className="eyebrow">Guardrails</div>
          <h3>How to read this report</h3>
        </div>
        <ul>
          {inv.guardrails.map((guardrail) => (
            <li key={guardrail}>{guardrail}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}

function ScoreTile({
  label,
  value,
  suffix,
  digits = 0
}: {
  label: string;
  value: number | null;
  suffix: string;
  digits?: number;
}) {
  return (
    <div className="score-tile">
      <span>{label}</span>
      <strong>
        {value == null ? "—" : `${formatNumber(value, digits)}${suffix}`}
      </strong>
    </div>
  );
}

function SnapshotCard({
  label,
  value,
  helper
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="card snapshot-card">
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </div>
  );
}

function NarrativeItem({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="narrative-item">
      <span>{label}</span>
      <p>{value}</p>
    </div>
  );
}

function WorkspaceLoading() {
  return (
    <div className="workspace-page">
      <div className="skeleton skeleton-card" />
    </div>
  );
}

function PageError({
  title,
  message
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="error-card workspace-page">
      <h2>{title}</h2>
      <p>{message}</p>
    </div>
  );
}
