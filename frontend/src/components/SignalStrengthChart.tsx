import type { ActivityPoint } from "../types";
import {linePath} from "../lib/chartSegments";
export function SignalStrengthChart({points,height=250}:{points:ActivityPoint[];height?:number}){
  const valid=points.filter(p=>typeof p.evidence_confidence==="number");
  if(!valid.length)return <div className="pdf-chart-empty">Evidence Confidence belum tersedia.</div>;
  const W=430,L=38,R=62,T=18,B=30,cw=W-L-R,ch=height-T-B;
  const x=(i:number)=>L+i/Math.max(1,points.length-1)*cw,y=(v:number)=>T+(100-v)/100*ch;
  const d=linePath(points,p=>p.evidence_confidence,x,y);
  return <div className="pdf-strength-wrap"><svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label="Signal strength over time; gaps are unknown">
    <rect x={L} y={y(100)} width={cw} height={y(70)-y(100)} className="strength-zone strong"/><rect x={L} y={y(70)} width={cw} height={y(40)-y(70)} className="strength-zone moderate"/><rect x={L} y={y(40)} width={cw} height={y(0)-y(40)} className="strength-zone weak"/>
    {[0,25,50,75,100].map(v=><g key={v}><line className="pdf-chart-grid" x1={L} x2={W-R} y1={y(v)} y2={y(v)}/><text className="pdf-chart-axis" x={L-7} y={y(v)+4} textAnchor="end">{v}</text></g>)}
    {points.map((p,i)=>p.spot_hit===true?<rect key={`a${i}`} className="strength-spot-band" x={Math.max(L,x(i)-3)} width="6" y={T} height={ch}/>:null)}
    <path className="pdf-strength-line" d={d}/>{points.map((p,i)=>p.evidence_confidence==null?null:<circle key={p.date} className="pdf-strength-dot" cx={x(i)} cy={y(p.evidence_confidence)} r="3"/>)}
    <text className="strength-label strong" x={W-R+8} y={y(84)}>Strong</text><text className="strength-label moderate" x={W-R+8} y={y(55)}>Moderate</text><text className="strength-label weak" x={W-R+8} y={y(20)}>Weak</text>
  </svg><p className="strength-band-note">Garis terputus saat confidence belum diketahui. Band merupakan panduan visual.</p></div>;
}
