import type { ActivityPoint } from "../types";

export function CandlestickVolumeChart({points,height=250}:{points:ActivityPoint[];height?:number}){
  const rows=points.filter(p=>p.open!=null&&p.high!=null&&p.low!=null&&p.close!=null);
  if(rows.length<2) return <div className="pdf-chart-empty">OHLC data unavailable for this ticker in the current snapshot.</div>;
  const W=900,L=56,R=20,T=20,B=34,VH=48,GAP=10,PH=height-T-B-VH-GAP,cw=W-L-R;
  const highs=rows.map(p=>p.high as number), lows=rows.map(p=>p.low as number); let min=Math.min(...lows),max=Math.max(...highs);const pad=(max-min)*.08||1;min-=pad;max+=pad;
  const maxVol=Math.max(...rows.map(p=>p.volume??0),1); const step=cw/rows.length; const body=Math.max(4,Math.min(10,step*.55));
  const x=(i:number)=>L+step*i+step/2; const y=(v:number)=>T+((max-v)/(max-min))*PH; const vy=(v:number)=>T+PH+GAP+VH-(v/maxVol)*VH;
  const ticks=Array.from({length:4},(_,i)=>max-(max-min)*(i/3)); const labels=[0,Math.floor((rows.length-1)/2),rows.length-1];
  return <div className="pdf-candle-wrap"><svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label="Candlestick and volume history">
    {ticks.map((v,i)=><g key={i}><line className="pdf-chart-grid" x1={L} x2={W-R} y1={y(v)} y2={y(v)}/><text className="pdf-chart-axis" x={L-8} y={y(v)+4} textAnchor="end">{formatPrice(v)}</text></g>)}
    {rows.map((p,i)=>{const o=p.open as number,h=p.high as number,l=p.low as number,c=p.close as number;const up=c>=o;const yy=Math.min(y(o),y(c)),hh=Math.max(2,Math.abs(y(o)-y(c)));return <g key={p.date}><line className={up?"candle-wick up":"candle-wick down"} x1={x(i)} x2={x(i)} y1={y(h)} y2={y(l)}/><rect className={up?"candle-body up":"candle-body down"} x={x(i)-body/2} width={body} y={yy} height={hh}/>{p.spot_hit&&<g><line className="spot-marker-line" x1={x(i)} x2={x(i)} y1={T} y2={T+PH+VH+GAP}/><circle className="spot-marker-dot" cx={x(i)} cy={T+8} r="6"/><text className="spot-marker-text" x={x(i)} y={T+11} textAnchor="middle">!</text></g>}<rect className={up?"volume-bar up":"volume-bar down"} x={x(i)-body/2} width={body} y={vy(p.volume??0)} height={T+PH+GAP+VH-vy(p.volume??0)}/></g>})}
    {labels.map(i=><text key={i} className="pdf-chart-axis" x={x(i)} y={height-8} textAnchor={i===0?"start":i===rows.length-1?"end":"middle"}>{shortDate(rows[i].date)}</text>)}
  </svg><div className="pdf-chart-legend"><span><i className="candle-up"/>Up session</span><span><i className="candle-down"/>Down session</span><span><i className="volume"/>Volume</span><span><i className="spot"/>Hard Spot hit</span></div></div>
}
function shortDate(v:string){const d=new Date(`${v}T00:00:00`);return new Intl.DateTimeFormat("en-GB",{day:"numeric",month:"short"}).format(d)}
function formatPrice(v:number){return new Intl.NumberFormat("en-US",{maximumFractionDigits:0}).format(v)}
