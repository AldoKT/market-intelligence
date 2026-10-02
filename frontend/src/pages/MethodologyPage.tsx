import { useEffect, useState } from "react";
import { getMethodology, getReactionValidation } from "../lib/api";
import type { MethodologyPayload, ReactionValidationPayload } from "../types";
import { formatNumber } from "../lib/format";
import { HistoricalReactionProfile } from "../components/HistoricalReactionProfile";

const FRAMEWORK = [
  ["S", "Spot", "Detect compressed price behavior with abnormal trading activity."],
  ["I", "Investigate", "Organize supporting and contradicting evidence around the flagged behavior."],
  ["G", "Gauge", "Track whether evidence persists across subsequent sessions."],
  ["N", "Narrative", "Translate structured facts into an inspectable 5W+1H explanation."],
  ["A", "Assess", "Show evidence consistency, uncertainty, and opposing signals."],
  ["L", "Look Ahead", "State conditions to monitor next, without forecasting a target price."]
];

export function MethodologyPage() {
  const [data, setData] = useState<MethodologyPayload | null>(null);
  const [reaction, setReaction] = useState<ReactionValidationPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    getMethodology()
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
  }, []);

  if (error) {
    return (
      <div className="error-card">
        <h2>Unable to load Methodology</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (!data) {
    return <div className="skeleton skeleton-card" />;
  }

  return (
    <>
      <section className="page-header">
        <div>
          <div className="eyebrow magenta">Methodology</div>
          <h1>{data.candidate_name}</h1>
          <p>
            SIGNAL is a market-intelligence screening and investigation
            engine. Reaction Validation tests whether detected setups carry
            directional information, while the core methodology keeps every
            detection traceable from raw metrics to lifecycle state.
          </p>
        </div>

        <div className="method-status-card">
          <span>STATUS</span>
          <strong>{data.status.replaceAll("_", " ")}</strong>
        </div>
      </section>

      <section className="framework-grid">
        {FRAMEWORK.map(([letter, title, text]) => (
          <div className="card framework-card" key={letter}>
            <div className="framework-letter">{letter}</div>
            <div>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="method-kpi-grid">
        <MethodKpi
          label="Eligible observations"
          value={String(data.basis.eligible_observations)}
        />
        <MethodKpi
          label="Eligible tickers"
          value={String(data.basis.eligible_symbols)}
        />
        <MethodKpi
          label="Hard Spot hits"
          value={String(data.basis.spot_hits)}
        />
        <MethodKpi
          label="Episodes"
          value={String(data.basis.baseline_investigation_episodes)}
        />
        <MethodKpi
          label="Sensitivity combinations"
          value={String(data.basis.sensitivity_grid_combinations)}
        />
        <MethodKpi
          label="Sensitive episodes reviewed"
          value={String(data.basis.peak_state_sensitive_episodes_reviewed)}
        />
      </section>

      {reaction && (
        <HistoricalReactionProfile
          data={reaction}
          title="Reaction Validation Profile"
        />
      )}

      <section className="methodology-grid">
        <div className="card method-card">
          <div className="eyebrow">Spot</div>
          <h2>Hard opening gate</h2>

          <FormulaLine
            label="Compression Score"
            value={`≥ ${data.spot_gate.compression_score_min}`}
          />
          <FormulaLine
            label="Activity Score"
            value={`≥ ${data.spot_gate.activity_score_min}`}
          />
          <FormulaLine
            label="Core relative threshold"
            value={`≥ ${formatNumber(
              data.spot_gate.core_relative_min,
              2
            )}×`}
          />
          <FormulaLine
            label="Minimum core metrics"
            value={`≥ ${data.spot_gate.minimum_core_metrics}`}
          />

          <div className="method-note">
            A hard Spot can open an investigation. Soft support cannot.
          </div>
        </div>

        <div className="card method-card">
          <div className="eyebrow">Gauge</div>
          <h2>Persistence & lifecycle</h2>

          <FormulaLine
            label="Support Compression"
            value={`≥ ${data.persistence_and_lifecycle.support_compression_min}`}
          />
          <FormulaLine
            label="Close after"
            value={`${data.persistence_and_lifecycle.close_after_consecutive_unsupported_sessions} unsupported sessions`}
          />
          <FormulaLine
            label="Established support"
            value={`${data.persistence_and_lifecycle.established_support_sessions_in_last_5_min}/5 sessions`}
          />
          <FormulaLine
            label="Established hard hits"
            value={`≥ ${data.persistence_and_lifecycle.established_hard_hits_in_episode_min}`}
          />

          <div className="lifecycle-flow">
            {[
              "EMERGING",
              "DEVELOPING",
              "ESTABLISHED",
              "WEAKENING",
              "CLOSED"
            ].map((state, index, arr) => (
              <div className="lifecycle-step-wrap" key={state}>
                <span className="lifecycle-step">{state}</span>
                {index < arr.length - 1 && (
                  <span className="lifecycle-arrow">→</span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="card method-card">
          <div className="eyebrow">Context</div>
          <h2>Context Specificity</h2>
          <p>{data.context_specificity.applicability_guard}</p>
          <p>{data.context_specificity.role}</p>

          <div className="context-method-list">
            <span>Stock-specific activity</span>
            <span>Peer-clustered activity</span>
            <span>Market-wide activity</span>
            <span>Mixed context</span>
          </div>
        </div>

        <div className="card method-card">
          <div className="eyebrow">Evidence Confidence</div>
          <h2>What the score means</h2>
          <p>
            Evidence Confidence is a consistency/support score for an
            active investigation. It is not the probability that price
            will rise and does not generate a buy/sell recommendation.
          </p>
          <div className="confidence-explainer">
            <div>
              <strong>Compression</strong>
              <span>25%</span>
            </div>
            <div>
              <strong>Activity</strong>
              <span>30%</span>
            </div>
            <div>
              <strong>Persistence</strong>
              <span>20%</span>
            </div>
            <div>
              <strong>Participation</strong>
              <span>15%</span>
            </div>
            <div>
              <strong>Flow</strong>
              <span>10%</span>
            </div>
          </div>
        </div>
      </section>

      <section className="card review-findings-card">
        <div className="section-heading">
          <div>
            <div className="eyebrow">Calibration Review</div>
            <h3>Why these thresholds were retained</h3>
          </div>
        </div>

        <div className="review-findings-grid">
          {Object.entries(data.review_findings).map(([key, value]) => (
            <div key={key}>
              <strong>{key.replaceAll("_", " ")}</strong>
              <p>{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card limitations-card">
        <div>
          <div className="eyebrow">Limitations</div>
          <h3>What SIGNAL does not claim</h3>
        </div>
        <ul>
          {data.important_limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </>
  );
}

function MethodKpi({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="card method-kpi">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function FormulaLine({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="formula-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
