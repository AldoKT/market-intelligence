import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getActivity, getSummary } from "../lib/api";
import type { ActivityPayload, SummaryPayload } from "../types";
import { ConfidenceGauge } from "../components/ConfidenceGauge";
import { StatusBadge } from "../components/StatusBadge";
import { PdfAreaChart } from "../components/PdfAreaChart";
import { formatDate, formatNumber } from "../lib/format";
import { companyName, humanGroup } from "../lib/companies";

export function SummaryPage(){
  const {symbol=""}=useParams(); const navigate=useNavigate();
  const [data,setData]=useState<SummaryPayload|null>(null); const [activity,setActivity]=useState<ActivityPayload|null>(null); const [error,setError]=useState<string|null>(null);
  useEffect(()=>{let alive=true;Promise.all([getSummary(symbol),getActivity(symbol).catch(()=>null)]).then(([s,a])=>{if(alive){setData(s);setActivity(a)}}).catch((e:Error)=>alive&&setError(e.message));return()=>{alive=false;};},[symbol]);
  const pricePoints=useMemo(()=>activity?.series.slice(-30).map(p=>({date:p.date,value:p.close}))??[],[activity]);
  if(error)return <div className="error-card workspace-page"><h2>Unable to load Summary</h2><p>{error}</p></div>;
  if(!data)return <div className="workspace-page"><div className="skeleton skeleton-card"/></div>;
  const inv=data.investigation;
  const close=inv.metrics.close;
  const series=activity?.series.filter(p=>p.close!=null)??[]; const prev=series.length>1?series[series.length-2].close:null; const change=close!=null&&prev?((close-prev)/prev)*100:null;
  const confSeries=(activity?.series??[]).filter(p=>p.evidence_confidence!=null); const prevConf=confSeries.length>1?confSeries[confSeries.length-2].evidence_confidence:null; const confDelta=inv.confidence.evidence_confidence!=null&&prevConf!=null?inv.confidence.evidence_confidence-prevConf:null;
  const positive=inv.look_ahead.filter(x=>x.current_status==="MET").slice(0,3); const negative=inv.look_ahead.filter(x=>x.current_status!=="MET").slice(0,3);
  return <section className="workspace-page v23-summary-page">
    <section className="v23-summary-top">
      <article className="card v23-report-card">
        <div className="v23-report-label">☆ &nbsp; INVESTIGATION REPORT</div>
        <div className="v23-report-grid">
          <div className="v23-report-copy"><h2>{inv.identity.symbol}</h2><div className="v23-company-row"><strong>{companyName(inv.identity.symbol,inv.identity.company_name)}</strong><span>{humanGroup(inv.identity.peer_group)}</span><span>IDX30</span></div><div className="v23-pattern-row"><h3>{inv.hypothesis}</h3><StatusBadge state={inv.state}/></div><p>{summaryNarrative(inv)}</p><button className="v23-primary" onClick={()=>navigate(`/investigations/${inv.identity.symbol}/activity`)}>View Evidence &nbsp; →</button></div>
          <div className="v23-report-confidence"><span>EVIDENCE CONFIDENCE &nbsp;ⓘ</span><ConfidenceGauge value={inv.confidence.evidence_confidence} compact/><small>/100</small></div>
          <div className="v23-report-market"><div className="v23-report-price"><span>Last Price (IDR)</span><strong>{close==null?'—':formatNumber(close,0)}</strong>{change!=null&&<em className={change>=0?'pos':'neg'}>{change>=0?'▲':'▼'} {change>=0?'+':''}{formatNumber(change,2)}%</em>}</div><div className="v23-summary-chart"><PdfAreaChart points={pricePoints} height={150} showBand={false}/></div></div>
        </div>
      </article>
      <aside className="card v23-status-card"><div className="v23-status-head"><span className="v23-status-icon">▥</span><div><span>Investigation Status</span><StatusBadge state={inv.state}/></div></div><h3>{statusTitle(inv.state)}</h3><p>{statusExplanation(inv.state)}</p>{confDelta!=null&&<div className={`v23-status-change ${confDelta>=0?'up':'down'}`}><b>{confDelta>=0?'↑':'↓'}</b><div><strong>{confDelta>=0?'Stronger than previous session':'Weaker than previous session'}</strong><span>Evidence Confidence {formatNumber((prevConf??0),0)} → {formatNumber(inv.confidence.evidence_confidence??0,0)}</span></div></div>}<div className="v23-status-rows"><Row label="First Detected" value={formatDate(inv.opened_at)}/><Row label="Last Updated" value={formatDate(inv.as_of)}/><Row label="Total Evidence Points" value={`${inv.supporting_evidence.length+inv.contradicting_evidence.length} indicators`}/><Row label="Monitoring Status" value={inv.active?'Active':'Inactive'}/></div></aside>
    </section>

    <section className="card v23-evidence-snapshot"><div className="v23-section-head"><div><h3>Evidence Snapshot</h3><span>Quick view of key signals from this investigation.</span></div><span>How we calculate these signals? &nbsp;ⓘ</span></div><div className="v23-snapshot-grid"><Snapshot icon="⌁" label="Price Compression" value={inv.metrics.current_5d_range_pct==null?'—':`${formatNumber(inv.metrics.current_5d_range_pct,2)}%`} helper={`Current 5-session range; baseline ${inv.metrics.baseline_5d_range_pct==null?'—':`${formatNumber(inv.metrics.baseline_5d_range_pct,2)}%`}.`}/><Snapshot icon="▥" label="Relative Activity" value={inv.metrics.relative_turnover==null?'—':`${formatNumber(inv.metrics.relative_turnover,2)}x`} helper="Turnover relative to the 20-session baseline."/><Snapshot icon="◷" label="Persistence" value={`${inv.persistence.support_sessions_in_last_5} / 5`} helper={`${inv.persistence.hard_hits_total_in_episode} hard Spot hit(s) in the episode.`}/><Snapshot icon="◎" label="Context Specificity" value={inv.context.specificity_score==null?'N/A':`${formatNumber(inv.context.specificity_score,0)}/100`} helper={human(inv.context.scope)}/></div></section>

    <section className="v23-summary-bottom">
      <article className="card v23-sees-card"><div className="v23-card-title"><span>●</span><strong>What SIGNAL Sees</strong><i>Key Insight</i></div><p>{inv.narrative_5w1h.what} {inv.narrative_5w1h.why}</p></article>
      <article className="card v23-narrative-card"><div className="v23-card-title"><span>▣</span><strong>5W + 1H Narrative</strong></div><div className="v23-narrative-grid"><Narr label="What" value={inv.narrative_5w1h.what}/><Narr label="Who" value={inv.narrative_5w1h.who}/><Narr label="When" value={inv.narrative_5w1h.when}/><Narr label="Why" value={inv.narrative_5w1h.why}/><Narr label="Where" value={inv.narrative_5w1h.where}/><Narr label="How" value={inv.narrative_5w1h.how}/></div></article>
      <article className="card v23-look-card"><div className="v23-card-title"><span>♧</span><strong>Look Ahead</strong></div><LookBlock title="What would strengthen the hypothesis?" kind="up" items={positive.length?positive:inv.look_ahead.slice(0,3)}/><LookBlock title="What would weaken the hypothesis?" kind="down" items={negative.length?negative:inv.look_ahead.slice(-3)}/></article>
    </section>
  </section>;
}
function Row({label,value}:{label:string;value:string}){return <div><span>{label}</span><strong>{value}</strong></div>}
function Snapshot({icon,label,value,helper}:{icon:string;label:string;value:string;helper:string}){return <div className="v23-snapshot"><b>{icon}</b><div><span>{label} &nbsp;ⓘ</span><strong>{value}</strong><small>{helper}</small></div></div>}
function Narr({label,value}:{label:string;value:string}){return <div><span>{label}</span><p>{value}</p></div>}
function LookBlock({title,kind,items}:{title:string;kind:'up'|'down';items:Array<{condition_id:string;label:string;note:string}>}){return <div className={`v23-look-block ${kind}`}><b>{kind==='up'?'↑':'↓'}</b><div><strong>{title}</strong><ul>{items.map(i=><li key={i.condition_id}>{i.label}</li>)}</ul></div></div>}
function statusTitle(state:string){return state==='ESTABLISHED'?'Evidence is persistent':state==='DEVELOPING'?'Investigation is developing':state==='WEAKENING'?'Continuation is weakening':state==='EMERGING'?'New investigation opened':'Investigation status'}
function statusExplanation(state:string){if(state==='WEAKENING')return'Latest session no longer supports the hypothesis; monitor the closure rule.';if(state==='ESTABLISHED')return'Evidence has persisted across multiple sessions under the frozen lifecycle rules.';if(state==='DEVELOPING')return'The pattern has repeated support but has not yet met Established requirements.';return'The hard Spot gate opened a new investigation. Confirmation from later sessions is not yet available.'}
function summaryNarrative(inv:SummaryPayload['investigation']){return `${inv.hypothesis} is ${human(inv.state).toLowerCase()} with ${inv.persistence.support_sessions_in_last_5}/5 supporting sessions, ${inv.persistence.hard_hits_total_in_episode} hard Spot hit(s), and ${inv.metrics.relative_turnover==null?'unavailable':`${formatNumber(inv.metrics.relative_turnover,2)}x`} relative turnover.`}
function human(v:string){return v.replaceAll('_',' ').toLowerCase().replace(/\b\w/g,c=>c.toUpperCase())}
