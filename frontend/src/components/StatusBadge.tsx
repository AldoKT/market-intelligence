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

export function StatusBadge({ state }: { state: string | null }) {
  return (
    <span className={(state == null ? null : stateClass[state]) ?? "badge badge-muted"}>
      {state == null ? "Belum dapat dinilai" : humanize(state)}
    </span>
  );
}
