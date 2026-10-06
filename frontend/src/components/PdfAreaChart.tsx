import { useId } from "react";
import { linePath, segments } from "../lib/chartSegments";

export interface AreaChartPoint {
  date: string;
  value: number | null;
  baseline?: number | null;
  lower?: number | null;
  upper?: number | null;
  anomaly?: boolean;
}

export function PdfAreaChart({
  points,
  height=250,
  valueFormatter=(v)=>formatCompact(v),
  baselineLabel="20D Baseline",
  showBand=true,
  anomalyLabel="Anomaly Period"
}:{
  points:AreaChartPoint[];
  height?:number;
  valueFormatter?:(v:number)=>string;
  baselineLabel?:string;
  showBand?:boolean;
  anomalyLabel?:string;
}){
  const id=useId().replaceAll(":","");
  const usable=points.filter((p):p is AreaChartPoint & {value:number}=>typeof p.value==="number"&&Number.isFinite(p.value));
  if(usable.length<2) return <div className="pdf-chart-empty">Series unavailable</div>;
  const W=900,L=60,R=24,T=24,B=38,cw=W-L-R,ch=height-T-B;
  const vals:number[]=[];
  usable.forEach(p=>{ vals.push(p.value); if(typeof p.baseline==="number") vals.push(p.baseline); if(typeof p.lower==="number") vals.push(p.lower); if(typeof p.upper==="number") vals.push(p.upper); });
  let min=Math.min(...vals), max=Math.max(...vals); if(min===max){min-=1;max+=1;} const pad=(max-min)*.09; min-=pad;max+=pad;
  const x=(i:number)=>L+(i/Math.max(1,points.length-1))*cw;
  const y=(v:number)=>T+((max-v)/(max-min))*ch;
  const line=linePath(points,p=>p.value,x,y);
  const area=segments(points,p=>typeof p.value==="number"&&Number.isFinite(p.value)).map(group=>`${group.map(({point,index},i)=>`${i?"L":"M"} ${x(index)} ${y(point.value!)}`).join(" ")} L ${x(group.at(-1)!.index)} ${T+ch} L ${x(group[0].index)} ${T+ch} Z`).join(" ");
  const base=linePath(points,p=>p.baseline,x,y);
  const band=segments(points,p=>typeof p.upper==="number"&&typeof p.lower==="number").filter(group=>group.length>1).map(group=>[...group.map(({point,index},j)=>`${j?"L":"M"} ${x(index)} ${y(point.upper!)}`),...group.slice().reverse().map(({point,index})=>`L ${x(index)} ${y(point.lower!)}`),"Z"].join(" ")).join(" ");
  const ticks=Array.from({length:5},(_,i)=>max-(max-min)*(i/4));
  const labels=[...new Set([0,Math.floor((points.length-1)*.25),Math.floor((points.length-1)*.5),Math.floor((points.length-1)*.75),points.length-1])];
  const last=usable.at(-1)!;
  return <div className="pdf-activity-chart-wrap">
    <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label="Market activity chart">
      <defs><linearGradient id={`area-${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ef2a83" stopOpacity=".30"/><stop offset="100%" stopColor="#ef2a83" stopOpacity=".02"/></linearGradient></defs>
      {ticks.map((v,i)=><g key={i}><line className="pdf-chart-grid" x1={L} x2={W-R} y1={y(v)} y2={y(v)}/><text className="pdf-chart-axis" x={L-10} y={y(v)+4} textAnchor="end">{valueFormatter(v)}</text></g>)}
      {points.map((p,i)=>p.anomaly?<rect key={`a${i}`} className="pdf-chart-anomaly" x={Math.max(L,x(i)-cw/usable.length*.55)} width={Math.max(7,cw/usable.length*1.1)} y={T} height={ch}/>:null)}
      {showBand&&band&&<path className="pdf-chart-normal-band" d={band}/>} 
      {base&&<path className="pdf-chart-baseline" d={base}/>} 
      <path d={area} fill={`url(#area-${id})`}/><path className="pdf-chart-series" d={line}/>
      <circle className="pdf-chart-last-dot" cx={x(points.indexOf(last))} cy={y(last.value)} r="4"/>
      {labels.map(i=><text key={i} className="pdf-chart-axis" x={x(i)} y={height-10} textAnchor={i===0?"start":i===points.length-1?"end":"middle"}>{shortDate(points[i].date)}</text>)}
    </svg>
    <div className="pdf-chart-legend"><span><i className="actual"/>Actual</span>{base&&<span><i className="baseline"/>{baselineLabel}</span>}{showBand&&band&&<span><i className="normal"/>Normal Range (±1 Std Dev)</span>}{usable.some(p=>p.anomaly)&&<span><i className="anomaly"/>{anomalyLabel}</span>}</div>
  </div>;
}

function shortDate(v:string){const d=new Date(`${v}T00:00:00`);return new Intl.DateTimeFormat("en-GB",{day:"numeric",month:"short"}).format(d)}
function formatCompact(v:number){const a=Math.abs(v);if(a>=1e9)return`${(v/1e9).toFixed(1)}B`;if(a>=1e6)return`${(v/1e6).toFixed(1)}M`;if(a>=1e3)return`${(v/1e3).toFixed(1)}K`;return v.toFixed(a<10?2:0)}
