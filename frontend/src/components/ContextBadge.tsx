import { humanize } from "../lib/format";

export function ContextBadge({
  scope
}: {
  scope: string | null | undefined;
}) {
  if (!scope) return <span className="muted">—</span>;

  return (
    <span className="context-badge">
      {humanize(scope)}
    </span>
  );
}
