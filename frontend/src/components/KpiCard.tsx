export function KpiCard({
  label,
  value,
  helper
}: {
  label: string;
  value: number | string;
  helper?: string;
}) {
  return (
    <div className="card kpi-card">
      <div className="eyebrow">{label}</div>
      <div className="kpi-value">{value}</div>
      {helper && <div className="helper-text">{helper}</div>}
    </div>
  );
}
