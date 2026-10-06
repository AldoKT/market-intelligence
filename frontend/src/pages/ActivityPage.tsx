import { useEffect, useMemo, useState } from "react";
import { PilotQualityNotice } from "../components/PilotQualityNotice";
import { useParams } from "react-router-dom";
import { getActivity } from "../lib/api";
import type { ActivityPayload, ActivityPoint } from "../types";
import { PdfAreaChart } from "../components/PdfAreaChart";
import { formatNumber } from "../lib/format";

type MetricKey="price"|"transactions"|"turnover"|"avgTrade";
type Resolved={label:string;unit:"price"|"count"|"idr";actual:keyof ActivityPoint;baseline?:keyof ActivityPoint;relative?:keyof ActivityPoint};
const DEFS:Record<MetricKey,Resolved>={
  price:{label:"Price",unit:"price",actual:"close"},
  transactions:{label:"Transaction Count",unit:"count",actual:"transaction_count",baseline:"transaction_count_baseline_20d",relative:"relative_transaction_count"},
  turnover:{label:"Turnover",unit:"idr",actual:"turnover_idr",baseline:"turnover_baseline_20d",relative:"relative_turnover"},
  avgTrade:{label:"Avg. Trade Value",unit:"idr",actual:"avg_trade_value_idr",baseline:"avg_trade_value_baseline_20d",relative:"relative_avg_trade_value"}
};

export function ActivityPage(){
  const {symbol=""}=useParams(); const [data,setData]=useState<ActivityPayload|null>(null); const [metric,setMetric]=useState<MetricKey>('turnover'); const [windowSize,setWindowSize]=useState(20); const [error,setError]=useState<string|null>(null);
  useEffect(()=>{let alive=true;getActivity(symbol).then(p=>alive&&setData(p)).catch((e:Error)=>alive&&setError(e.message));return()=>{alive=false;};},[symbol]);
  const view=useMemo(()=>data?resolveMetric(data,metric,windowSize):null,[data,metric,windowSize]);
  if(error)return <div className="error-card workspace-page"><h2>Unable to load Market Activity</h2><p>{error}</p></div>;
  if(!data||!view)return <div className="workspace-page"><div className="skeleton skeleton-card"/></div>;
  return <section className="workspace-page v23-activity-page">
    <PilotQualityNotice data={data}/>
    {data.quality&&<p className="pilot-chart-note">Nilai aktual tetap tersedia jika sumber sesi cocok. Baseline detector ditampilkan sebagai perkiraan dari nilai aktual ÷ rasio tersimpan; sesi yang ditahan tetap kosong. Garis terputus pada data kosong.</p>}
    <section className="v23-activity-selectors">{(Object.keys(DEFS) as MetricKey[]).map(k=><MetricSelector key={k} k={k} active={metric===k} data={data} onClick={()=>setMetric(k)}/>)}</section>
    <section className="v23-activity-layout">
      <article className="card v23-activity-chart-card"><div className="v23-activity-chart-head"><div><h3>Market Activity — {view.title}</h3><span>ⓘ</span></div><div className="v23-window-tabs">{[5,20,60].map(n=><button key={n} className={windowSize===n?'active':''} onClick={()=>setWindowSize(n)}>{n}D</button>)}</div></div><PdfAreaChart points={view.points} height={300} valueFormatter={v=>formatMetric(v,view.unit,view.relative)} baselineLabel={view.relative?'Relative baseline = 1.00x':data.quality?'Baseline detector (≈)':'20D Baseline'} showBand={!view.relative&&!data.quality}/></article>
      <aside className="card v23-turnover-detail"><div className="v23-detail-title"><span>▣</span><h3>{view.title} Details</h3></div><Detail label="Current Value" value={formatMetric(view.current,view.unit,view.relative)}/><Detail label={data.quality?"Baseline detector (≈)":"20D Baseline"} value={formatMetric(view.baseline,view.unit,view.relative)}/><Detail label="Difference" value={view.diff==null?'—':`${view.diff>=0?'▲ +':'▼ '}${formatNumber(view.diff*100,1)}%`} positive={view.diff!=null?view.diff>=0:undefined}/><Detail label="Z-score" value={view.zscore==null?'Unavailable':`${view.zscore>=0?'+':''}${formatNumber(view.zscore,2)}`} positive={view.zscore==null?undefined:view.zscore>=0}/><Detail label="Peak in period" value={formatMetric(view.peak,view.unit,view.relative)} sub={view.peakDate}/><Detail label="Sessions above baseline" value={`${view.above}/${view.comparable}`} sub={view.comparable?`(${formatNumber(view.above/view.comparable*100,0)}%)`:"Baseline belum tersedia"}/>{view.relative&&<p className="v23-detail-note">Actual cached market value is unavailable for this ticker, so this panel explicitly shows the relative series. It is not labelled as IDR.</p>}</aside>
    </section>
    <section className="card v23-cross-card"><div className="v23-cross-title"><span>▥</span><h3>Cross-Metric Comparison</h3><span>ⓘ</span></div><div className="v23-cross-grid"><Cross label="Transaction Count" value={data.current.relative_transaction_count}/><Cross label="Turnover" value={data.current.relative_turnover}/><Cross label="Avg. Trade Value" value={data.current.relative_avg_trade_value}/><Cross label="Price Range" value={data.current.current_5d_range_pct} percent/></div></section>
  </section>;
}

export function resolveMetric(data:ActivityPayload,key:MetricKey,windowSize:number){
  const def=DEFS[key]; const rows=data.series.slice(-windowSize);
  const hasActual=rows.some(p=>typeof p[def.actual]==='number'); const relative=!hasActual&&!!def.relative; const actualKey=(relative?def.relative:def.actual)!;
  let baselines:Array<number|null>=[];
  if(relative) baselines=rows.map(()=>1);
  else if(data.quality) baselines=rows.map(p=>{const v=num(p[def.actual]),r=def.relative?num(p[def.relative]):null;return v!=null&&r!=null&&r>0?v/r:null;});
  else if(def.baseline) baselines=rows.map(p=>num(p[def.baseline!]));
  else baselines=rollingMedian(data.series.map(p=>num(p[def.actual])),20).slice(-windowSize);
  const actual=rows.map(p=>num(p[actualKey])); const std=relative||data.quality?rows.map(()=>null):rollingStd(data.series.map(p=>num(p[actualKey])),20).slice(-windowSize);
  const points=rows.map((p,i)=>({date:p.date,value:actual[i],baseline:baselines[i],lower:baselines[i]!=null&&std[i]!=null?Math.max(0,(baselines[i] as number)-(std[i] as number)):null,upper:baselines[i]!=null&&std[i]!=null?(baselines[i] as number)+(std[i] as number):null,anomaly:p.spot_hit===true}));
  const pairs=actual.map((v,i)=>({v,b:baselines[i],date:rows[i].date})).filter((x):x is {v:number;b:number|null;date:string}=>x.v!=null);
  const current=actual.at(-1)??null, baseline=baselines.at(-1)??null; const diff=current!=null&&baseline!=null&&baseline!==0?current/baseline-1:null;
  const peakRow=pairs.reduce<{v:number;date:string}|null>((m,x)=>!m||x.v>m.v?{v:x.v,date:x.date}:m,null); const above=pairs.filter(x=>x.b!=null&&x.v>x.b).length;
  const zscore=(!relative&&current!=null&&baseline!=null&&std.at(-1)!=null&&(std.at(-1) as number)>0)?(current-baseline)/(std.at(-1) as number):null;
  return {title:relative?`Relative ${def.label}`:def.label,unit:def.unit,relative,points,current,baseline,diff,peak:peakRow?.v??null,peakDate:peakRow?shortDate(peakRow.date):undefined,above,total:pairs.length,comparable:pairs.filter(x=>x.b!=null).length,zscore};
}
function MetricSelector({k,active,data,onClick}:{k:MetricKey;active:boolean;data:ActivityPayload;onClick:()=>void}){const d=DEFS[k];let value='—',helper='';if(k==='price'){const rows=data.series.filter(p=>p.close!=null);const a=rows.at(-1)?.close,b=rows.at(-2)?.close;const pct=a!=null&&b?((a-b)/b)*100:null;value=pct==null?'—':`${pct>=0?'+':''}${formatNumber(pct,1)}%`;helper='1D price change';}else{const r=k==='transactions'?data.current.relative_transaction_count:k==='turnover'?data.current.relative_turnover:data.current.relative_avg_trade_value;value=r==null?'—':`${r>=1?'+':''}${formatNumber((r-1)*100,0)}%`;helper='vs 20D baseline';}return <button className={`v23-metric-selector ${active?'active':''}`} onClick={onClick}><span className="v23-metric-icon">{k==='turnover'?'▣':'▥'}</span><div><span>{d.label}</span><strong>{value}</strong><small>{helper}</small></div></button>}
function Detail({label,value,sub,positive}:{label:string;value:string;sub?:string;positive?:boolean}){return <div className="v23-detail-row"><span>{label} &nbsp;ⓘ</span><div><strong className={positive===undefined?'':positive?'pos':'neg'}>{value}</strong>{sub&&<small>{sub}</small>}</div></div>}
function Cross({label,value,percent=false}:{label:string;value:number|null;percent?:boolean}){const delta=value==null?null:percent?value:(value-1)*100;const w=value==null?0:percent?Math.min(100,value*12):Math.min(100,Math.max(0,(value/3)*100));return <div className="v23-cross-item"><span className="v23-cross-icon">{percent?'⌁':'▥'}</span><div><span>{label}</span><strong className={delta!=null&&(!percent?delta>=0:true)?'pos':''}>{value==null?'—':percent?`${formatNumber(value,2)}%`:`${delta!>=0?'+':''}${formatNumber(delta!,0)}%`}</strong><small>{percent?'current 5D range':'vs 20D baseline'}</small><div className="v23-progress"><i style={{width:`${w}%`}}/></div></div></div>}
function num(v:unknown){return typeof v==='number'&&Number.isFinite(v)?v:null}
function rollingMedian(values:Array<number|null>,n:number){return values.map((_,i)=>{const s=values.slice(Math.max(0,i-n+1),i+1).filter((x):x is number=>x!=null).sort((a,b)=>a-b);if(!s.length)return null;const m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2})}
function rollingStd(values:Array<number|null>,n:number){return values.map((_,i)=>{const s=values.slice(Math.max(0,i-n+1),i+1).filter((x):x is number=>x!=null);if(s.length<3)return null;const mean=s.reduce((a,b)=>a+b,0)/s.length;return Math.sqrt(s.reduce((a,b)=>a+(b-mean)**2,0)/(s.length-1))})}
function formatMetric(v:number|null,unit:'price'|'count'|'idr',relative:boolean){if(v==null)return'—';if(relative)return`${formatNumber(v,2)}x`;if(unit==='idr')return`IDR ${compact(v)}`;if(unit==='count')return formatNumber(v,0);return formatNumber(v,0)}
function compact(v:number){const a=Math.abs(v);if(a>=1e12)return`${formatNumber(v/1e12,2)}T`;if(a>=1e9)return`${formatNumber(v/1e9,2)}B`;if(a>=1e6)return`${formatNumber(v/1e6,2)}M`;return formatNumber(v,0)}
function shortDate(v:string){const d=new Date(`${v}T00:00:00`);return new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric'}).format(d)}
