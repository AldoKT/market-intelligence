interface ChartPoint {
  date: string;
  value: number | null;
  baseline?: number | null;
  anomaly?: boolean;
}

export function ResearchChart({
  points,
  height = 300,
  suffix = "",
  threshold,
  thresholdLabel,
  baselineLabel = "20D baseline",
  showBaseline = true,
  emptyLabel = "Series unavailable"
}: {
  points: ChartPoint[];
  height?: number;
  suffix?: string;
  threshold?: number;
  thresholdLabel?: string;
  baselineLabel?: string;
  showBaseline?: boolean;
  emptyLabel?: string;
}) {
  const usable = points.filter((p): p is ChartPoint & { value: number } => typeof p.value === "number" && Number.isFinite(p.value));
  if (usable.length < 2) {
    return <div className="v2-chart-empty">{emptyLabel}</div>;
  }

  const width = 960;
  const left = 58;
  const right = 20;
  const top = 24;
  const bottom = 38;
  const baselineValues = usable.map(p => p.baseline).filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  const values = [...usable.map(p => p.value), ...baselineValues];
  if (typeof threshold === "number") values.push(threshold);
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) { min -= 1; max += 1; }
  const pad = (max - min) * 0.12;
  min -= pad; max += pad;
  const cw = width - left - right;
  const ch = height - top - bottom;
  const x = (i: number) => left + (i / Math.max(1, usable.length - 1)) * cw;
  const y = (v: number) => top + ((max - v) / (max - min)) * ch;
  const valuePath = usable.map((p,i) => `${i ? "L" : "M"} ${x(i).toFixed(2)} ${y(p.value).toFixed(2)}`).join(" ");
  const baselinePts = usable.map((p,i) => p.baseline == null ? null : {x:x(i),y:y(p.baseline)}).filter(Boolean) as Array<{x:number;y:number}>;
  const baselinePath = baselinePts.map((p,i) => `${i ? "L" : "M"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(" ");
  const ticks = Array.from({length:4},(_,i)=>({v:max-(max-min)*(i/3), y:top+ch*(i/3)}));
  const labels = [0, Math.floor((usable.length-1)/2), usable.length-1];
  const thresholdY = typeof threshold === "number" ? y(threshold) : null;

  return (
    <div className="v2-research-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Research time series">
        {ticks.map((t,i)=><g key={i}><line className="v2-chart-grid" x1={left} x2={width-right} y1={t.y} y2={t.y}/><text className="v2-chart-label" x={left-10} y={t.y+4} textAnchor="end">{formatAxis(t.v)}{suffix}</text></g>)}
        {usable.map((p,i)=>p.anomaly ? <rect key={`a-${i}`} className="v2-anomaly-band" x={Math.max(left, x(i)-cw/Math.max(usable.length,2)/2)} y={top} width={Math.max(5,cw/Math.max(usable.length,2))} height={ch}/> : null)}
        {thresholdY != null && <g><line className="v2-threshold-line" x1={left} x2={width-right} y1={thresholdY} y2={thresholdY}/><text className="v2-threshold-label" x={width-right} y={thresholdY-7} textAnchor="end">{thresholdLabel ?? "Threshold"}</text></g>}
        {showBaseline && baselinePts.length > 1 && <path className="v2-baseline-path" d={baselinePath}/>}        
        <path className="v2-value-path" d={valuePath}/>
        {usable.filter(p=>p.anomaly).map((p)=>{ const i=usable.indexOf(p); return <circle key={`${p.date}-${p.value}`} className="v2-anomaly-dot" cx={x(i)} cy={y(p.value)} r="4"/>; })}
        {labels.map(i=><text key={i} className="v2-chart-label" x={x(i)} y={height-10} textAnchor={i===0?"start":i===usable.length-1?"end":"middle"}>{shortDate(usable[i].date)}</text>)}
      </svg>
      <div className="v2-chart-legend">
        <span><i className="v2-legend-line"/>Actual / selected series</span>
        {showBaseline && baselinePts.length > 1 && <span><i className="v2-legend-dash"/>{baselineLabel}</span>}
        {usable.some(p=>p.anomaly) && <span><i className="v2-legend-band"/>Hard Spot session</span>}
      </div>
    </div>
  );
}

function formatAxis(v:number){
  const a=Math.abs(v);
  if(a>=1_000_000_000) return `${(v/1_000_000_000).toFixed(1)}B`;
  if(a>=1_000_000) return `${(v/1_000_000).toFixed(1)}M`;
  if(a>=1_000) return `${(v/1_000).toFixed(1)}K`;
  return v.toFixed(a<10?2:1);
}
function shortDate(value:string){
  const d=new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en-GB",{day:"2-digit",month:"short"}).format(d);
}
