import type { EvidenceItem } from "../types";
import { formatNumber, formatPercentRatio } from "../lib/format";

export function EvidenceCard({
  evidence
}: {
  evidence: EvidenceItem;
}) {
  const supporting = evidence.direction === "SUPPORTING";

  return (
    <div
      className={`evidence-card ${
        supporting ? "evidence-support" : "evidence-contradict"
      }`}
    >
      <div className="evidence-card-head">
        <div>
          <span className="eyebrow">
            {supporting ? "Supporting Evidence" : "Contradicting Evidence"}
          </span>
          <h4>{evidence.label}</h4>
        </div>

        <span className="evidence-symbol">
          {supporting ? "+" : "−"}
        </span>
      </div>

      <div className="evidence-values">
        {evidence.score != null && (
          <EvidenceValue
            label="Score"
            value={`${formatNumber(evidence.score, 1)}/100`}
          />
        )}

        {evidence.relative != null && (
          <EvidenceValue
            label={
              evidence.metric === "foreign_net_to_turnover"
                ? "Relative"
                : "Relative"
            }
            value={
              evidence.metric === "foreign_net_to_turnover"
                ? formatPercentRatio(evidence.relative, 1)
                : `${formatNumber(evidence.relative, 2)}×`
            }
          />
        )}

        {evidence.value != null && (
          <EvidenceValue
            label="Current"
            value={formatNumber(evidence.value, 2)}
          />
        )}

        {evidence.baseline != null && (
          <EvidenceValue
            label="Baseline"
            value={formatNumber(evidence.baseline, 2)}
          />
        )}
      </div>

      <p>{evidence.note}</p>
    </div>
  );
}

function EvidenceValue({
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
