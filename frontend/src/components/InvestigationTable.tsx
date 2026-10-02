import type { InvestigationListItem } from "../types";
import { ContextBadge } from "./ContextBadge";
import { StatusBadge } from "./StatusBadge";
import { formatNumber } from "../lib/format";

interface Props {
  items: InvestigationListItem[];
  selectedSymbol?: string | null;
  onSelect?: (item: InvestigationListItem) => void;
  compact?: boolean;
}

export function InvestigationTable({
  items,
  selectedSymbol,
  onSelect,
  compact = false
}: Props) {
  if (!items.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">○</div>
        <h3>No unusual behavior detected</h3>
        <p>
          No investigations match the current snapshot or filters.
        </p>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>State</th>
            <th>Confidence</th>
            {!compact && <th>Context</th>}
            <th>Rel. Activity</th>
            {!compact && <th>Range</th>}
            <th>Persistence</th>
          </tr>
        </thead>

        <tbody>
          {items.map((item) => (
            <tr
              key={item.symbol}
              className={
                selectedSymbol === item.symbol ? "row-selected" : ""
              }
              onClick={() => onSelect?.(item)}
            >
              <td>
                <div className="ticker-cell">
                  <strong>{item.symbol}</strong>
                  <span>{item.peer_group ?? "Unmapped"}</span>
                </div>
              </td>

              <td>
                <StatusBadge state={item.state} />
              </td>

              <td>
                <strong>
                  {item.evidence_confidence == null
                    ? "—"
                    : `${formatNumber(item.evidence_confidence, 0)}/100`}
                </strong>
              </td>

              {!compact && (
                <td>
                  <ContextBadge scope={item.context_scope} />
                </td>
              )}

              <td>
                {item.relative_turnover == null
                  ? "—"
                  : `${formatNumber(item.relative_turnover, 2)}×`}
              </td>

              {!compact && (
                <td>
                  {item.current_5d_range_pct == null
                    ? "—"
                    : `${formatNumber(item.current_5d_range_pct, 2)}%`}
                </td>
              )}

              <td>
                <span className="persistence-pill">
                  {item.persistence_hits}/{item.persistence_window}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
