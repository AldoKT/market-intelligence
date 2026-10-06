export function MiniSparkline({
  values,
  width = 120,
  height = 34,
  className = ""
}: {
  values: Array<number | null | undefined>;
  width?: number;
  height?: number;
  className?: string;
}) {
  const usable = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (usable.length < 2) return <span className="mini-sparkline-empty">—</span>;

  const min = Math.min(...usable);
  const max = Math.max(...usable);
  const span = max - min || 1;
  const pad = 3;
  const points = usable.map((v, i) => {
    const x = pad + (i / Math.max(1, usable.length - 1)) * (width - pad * 2);
    const y = pad + ((max - v) / span) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  return (
    <svg className={`mini-sparkline ${className}`} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline points={points} fill="none" />
    </svg>
  );
}
