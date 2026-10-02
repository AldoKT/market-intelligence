import { formatNumber } from "../lib/format";

export function ConfidenceGauge({
  value,
  compact = false
}: {
  value: number | null | undefined;
  compact?: boolean;
}) {
  const safe = value ?? 0;

  return (
    <div className={compact ? "gauge gauge-compact" : "gauge"}>
      <div className="gauge-ring">
        <svg viewBox="0 0 42 42" aria-hidden="true">
          <circle
            className="gauge-track"
            cx="21"
            cy="21"
            r="15.9155"
            fill="none"
            strokeWidth="3.4"
          />
          <circle
            className="gauge-value"
            cx="21"
            cy="21"
            r="15.9155"
            fill="none"
            strokeWidth="3.4"
            strokeDasharray={`${Math.max(0, Math.min(100, safe))} ${
              100 - Math.max(0, Math.min(100, safe))
            }`}
            strokeDashoffset="25"
          />
        </svg>
        <div className="gauge-number">
          {value == null ? "—" : formatNumber(value, 0)}
        </div>
      </div>

      {!compact && (
        <div>
          <div className="eyebrow">Evidence Confidence</div>
          <div className="helper-text">
            Consistency of current evidence, not a return probability.
          </div>
        </div>
      )}
    </div>
  );
}
