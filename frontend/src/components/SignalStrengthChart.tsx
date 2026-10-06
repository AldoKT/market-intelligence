import type { ActivityPoint } from "../types";
export function SignalStrengthChart({points,height=250}:{points:ActivityPoint[];height?:number}){
  const rows=points.filter(p=>typeof p.evidence_confidence==="number") as Array<ActivityPoint & {evidence_confidence:number}>;
  if(rows.length<2) return <div className="pdf-chart-empty">Signal-strength history is unavailable.</div>;
  const W=430,L=38,R=62,T=18,B=30,cw=W-L-R,ch=height-T-B; const x=(i:number)=>L+(i/(rows.length-1))*cw; const y=(v:number)=>T+((100-v)/100)*ch;
  const d=rows.map((p,i)=>`${i?"L":"M"} ${x(i)} ${y(p.evidence_confidence)}`).join(" ");
  return <div className="pdf-strength-wrap"><svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label="Signal strength over time">
    <rect x={L} y={y(100)} width={cw} height={y(70)-y(100)} className="strength-zone strong"/><rect x={L} y={y(70)} width={cw} height={y(40)-y(70)} className="strength-zone moderate"/><rect x={L} y={y(40)} width={cw} height={y(0)-y(40)} className="strength-zone weak"/>
    {[0,25,50,75,100].map(v=><g key={v}><line className="pdf-chart-grid" x1={L} x2={W-R} y1={y(v)} y2={y(v)}/><text className="pdf-chart-axis" x={L-7} y={y(v)+4} textAnchor="end">{v}</text></g>)}
    {rows.map((p,i)=>p.spot_hit?<rect key={`a${i}`} className="strength-spot-band" x={Math.max(L,x(i)-6)} width="12" y={T} height={ch}/>:null)}
    <path className="pdf-strength-line" d={d}/>{rows.map((p,i)=><circle key={p.date} className="pdf-strength-dot" cx={x(i)} cy={y(p.evidence_confidence)} r="3"/>)}
    <text className="strength-label strong" x={W-R+8} y={y(84)}>Strong</text><text className="strength-label moderate" x={W-R+8} y={y(55)}>Moderate</text><text className="strength-label weak" x={W-R+8} y={y(20)}>Weak</text>
  </svg><p className="strength-band-note">Visual reading bands only; detector lifecycle thresholds are unchanged.</p></div>
}
