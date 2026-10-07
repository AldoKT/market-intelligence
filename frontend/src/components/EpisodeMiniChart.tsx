import { useId } from "react";
import type { ActivityPoint, EpisodeSummary } from "../types";
import { episodeChartWindow } from "../lib/episodeChart";
import { linePath } from "../lib/chartSegments";

export function EpisodeMiniChart({ points, episode, symbol, loading, failed }: { points?: ActivityPoint[]; episode: EpisodeSummary; symbol: string; loading?: boolean; failed?: boolean }) {
  const id = useId().replace(/:/g, "");
  if (!points) return <div className="ov-mini-empty">{failed ? "Grafik belum tersedia" : loading ? "Memuat grafik…" : "Grafik belum tersedia"}</div>;
  const window = episodeChartWindow(points,episode);
  const prices = window.points.flatMap(p=>[p.close,p.low,p.high].filter((v): v is number=>v!=null && Number.isFinite(v)));
  if(!prices.length) return <div className="ov-mini-empty">Harga belum tersedia</div>;
  const min = Math.min(...prices), max = Math.max(...prices), span = max-min || Math.max(1,max*.02);
  const x = (i:number)=>12+i*272/Math.max(1,window.points.length-1);
  const y = (v:number)=>14+(max-v)*86/span;
  const step = 272/Math.max(1,window.points.length-1);
  const format = (v:number)=>v.toLocaleString("id-ID",{maximumFractionDigits:0});
  const date = (d:string)=>new Date(d+"T00:00:00").toLocaleDateString("id-ID",{day:"numeric",month:"short"});
  const last = window.points.filter(p=>p.close!=null && Number.isFinite(p.close)).at(-1);
  return <div className="ov-mini-chart">
    <div className="ov-mini-caption"><span>Price action</span><span className="ov-mini-key"><i aria-hidden="true"/>Hard spot · {window.hardSpots.length}</span></div>
    <svg viewBox="0 0 296 128" role="img" aria-labelledby={`${id}-title ${id}-desc`}>
      <title id={`${id}-title`}>Grafik harga {symbol}, investigasi {date(episode.opened_at)}</title>
      <desc id={`${id}-desc`}>Garis menunjukkan harga penutupan. {window.hardSpots.length} kotak berarsir menandai rentang low sampai high pada sesi hard spot dalam investigasi ini.</desc>
      <defs><pattern id={`${id}-hatch`} width="5" height="5" patternUnits="userSpaceOnUse"><path d="M-1 1L1 -1M0 5L5 0M4 6L6 4" stroke="#93c5fd" strokeWidth=".7" opacity=".45"/></pattern></defs>
      {[14,57,100].map(v=><line key={v} x1="12" x2="284" y1={v} y2={v} stroke="#3c4a5c" strokeDasharray="3 4"/>)}
      {window.hardSpots.map(p=>{const i=window.points.findIndex(v=>v.date===p.date);return <rect key={p.date} className="ov-hardspot-range" x={x(i)-Math.max(9,step*.8)/2} y={y(p.high!)} width={Math.max(9,step*.8)} height={Math.max(1,y(p.low!)-y(p.high!))} rx="2" fill={`url(#${id}-hatch)`} stroke="#93c5fd" strokeWidth="1.5"><title>{date(p.date)} · Hard spot · Low Rp {format(p.low!)} – High Rp {format(p.high!)}</title></rect>})}
      <path d={linePath(window.points,p=>p.close,x,y)} fill="none" stroke="#67e8f9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      {last && <circle cx={x(window.points.indexOf(last))} cy={y(last.close!)} r="3" fill="#67e8f9" stroke="#20262e" strokeWidth="1.5"/>}
      <text x="12" y="121" fill="#b8c5d6" fontSize="11">{date(window.points[0].date)}</text><text x="284" y="121" textAnchor="end" fill="#b8c5d6" fontSize="11">{date(window.points.at(-1)!.date)}</text>
    </svg>
    <div className="ov-mini-range"><span>Low <strong>Rp {format(min)}</strong></span><span>High <strong>Rp {format(max)}</strong></span></div>
  </div>;
}
