import { useMemo, useState } from "react";
import type {
  ReactionValidationHorizon,
  ReactionValidationPayload
} from "../types";
import { formatPercentRatio, humanize } from "../lib/format";

interface HistoricalReactionProfileProps {
  data: ReactionValidationPayload;
  currentAsOf?: string;
  respectPointInTime?: boolean;
  title?: string;
}

const DEFAULT_HORIZON = 5;

export function HistoricalReactionProfile({
  data,
  currentAsOf,
  respectPointInTime = false,
  title = "Historical Reaction Profile"
}: HistoricalReactionProfileProps) {
  const [selectedHorizon, setSelectedHorizon] = useState(DEFAULT_HORIZON);

  const protectedHistoricalView = Boolean(
    respectPointInTime &&
      currentAsOf &&
      currentAsOf < data.validation_as_of
  );

  const horizon = useMemo(() => {
    return (
      data.horizons.find(
        (item) => item.horizon_sessions === selectedHorizon
      ) ?? data.horizons[0]
    );
  }, [data.horizons, selectedHorizon]);

  if (protectedHistoricalView) {
    return (
      <section className="card reaction-profile-card reaction-profile-protected">
        <div className="section-heading reaction-profile-heading">
          <div>
            <div className="eyebrow">Research Validation</div>
            <h3>{title}</h3>
          </div>
          <span className="reaction-status-chip">Point-in-time protected</span>
        </div>

        <div className="reaction-protection-message">
          <div className="reaction-protection-icon" aria-hidden="true">
            ✓
          </div>
          <div>
            <strong>Post-snapshot reaction statistics are hidden here.</strong>
            <p>
              This page is a historical replay. SIGNAL does not expose research
              outcomes that were calculated after the current snapshot, so the
              investigation remains point-in-time clean.
            </p>
          </div>
        </div>

        <p className="reaction-profile-footnote">
          The current research validation can still be reviewed on the
          Methodology page. It is not used as an input to this historical
          investigation.
        </p>
      </section>
    );
  }

  if (!horizon) return null;

  return (
    <section className="card reaction-profile-card">
      <div className="section-heading reaction-profile-heading">
        <div>
          <div className="eyebrow">Research Validation</div>
          <h3>{title}</h3>
          <p className="reaction-profile-subtitle">
            SPOT_OPEN cohort versus eligible NO_INVESTIGATION controls on the
            same market date.
          </p>
        </div>

        <div className="reaction-profile-status-wrap">
          <span className="reaction-status-chip reaction-status-tentative">
            {humanize(data.status)}
          </span>
          <span className="reaction-status-subtle">
            ≤5-session robustness not established
          </span>
        </div>
      </div>

      <div className="reaction-horizon-tabs" role="tablist" aria-label="Reaction horizon">
        {data.horizons.map((item) => (
          <button
            className={
              item.horizon_sessions === horizon.horizon_sessions
                ? "reaction-horizon-button active"
                : "reaction-horizon-button"
            }
            key={item.horizon_sessions}
            onClick={() => setSelectedHorizon(item.horizon_sessions)}
            type="button"
          >
            +{item.horizon_sessions} session
            {item.horizon_sessions === 1 ? "" : "s"}
          </button>
        ))}
      </div>

      <div className="reaction-metric-grid">
        <ReactionMetric
          label="Positive close"
          signal={horizon.positive_close_rate}
          control={horizon.control_positive_close_rate}
        />
        <ReactionMetric
          label="Reached +2%"
          signal={horizon.reached_plus_2_rate}
          control={horizon.control_reached_plus_2_rate}
        />
        <ReactionMetric
          label="5D-close breakout"
          signal={horizon.breakout_5d_close_rate}
          control={horizon.control_breakout_5d_close_rate}
        />
        <ReactionMetric
          label="Close-based MFE"
          signal={horizon.mfe_close}
          control={horizon.control_mfe_close}
        />
      </div>

      <div className="reaction-profile-meta">
        <span>
          Cohort <strong>n={horizon.event_n}</strong>
        </span>
        <span>
          Validation sample {data.sample_period.start} → {data.sample_period.end}
        </span>
        <span>Research layer only — not a signal input</span>
      </div>

      <div className="reaction-guardrail">
        <strong>How to read this:</strong>
        <span>{data.guardrail}</span>
      </div>
    </section>
  );
}

function ReactionMetric({
  label,
  signal,
  control
}: {
  label: string;
  signal: number;
  control: number;
}) {
  const delta = signal - control;

  return (
    <div className="reaction-metric-card">
      <span className="reaction-metric-label">{label}</span>

      <div className="reaction-comparison-row">
        <div>
          <span>SIGNAL</span>
          <strong>{formatPercentRatio(signal, 1)}</strong>
        </div>
        <div>
          <span>CONTROL</span>
          <strong>{formatPercentRatio(control, 1)}</strong>
        </div>
      </div>

      <div className="reaction-delta">
        Δ {delta >= 0 ? "+" : ""}{(delta * 100).toFixed(1)} pp
      </div>
    </div>
  );
}
