import { humanize } from "../lib/format";

const stateClass: Record<string, string> = {
  ESTABLISHED: "badge badge-established",
  DEVELOPING: "badge badge-developing",
  EMERGING: "badge badge-emerging",
  WEAKENING: "badge badge-weakening",
  CLOSED: "badge badge-muted",
  NO_INVESTIGATION: "badge badge-muted",
  INELIGIBLE_PRICE_REGIME: "badge badge-muted"
};

export function StatusBadge({ state }: { state: string }) {
  return (
    <span className={stateClass[state] ?? "badge badge-muted"}>
      {humanize(state)}
    </span>
  );
}
