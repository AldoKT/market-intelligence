import {NavbarGlass} from "../components/NavbarGlass";
import {Link} from "react-router-dom";
import "../overview-mockups.css";
import "../summary-mockups.css";
import "../methodology-design.css";
import { useEffect, useState } from "react";
import { PilotMethodology } from "../components/PilotMethodology";
import { getMethodology, getOverview, getReactionValidation } from "../lib/api";
import type { MethodologyPayload, OverviewPayload, ReactionValidationPayload } from "../types";
import { HistoricalReactionProfile } from "../components/HistoricalReactionProfile";
import { StatusBadge } from "../components/StatusBadge";
import { formatNumber } from "../lib/format";

const FRAMEWORK=[
  ["S","Spot","Detect unusual market behaviour."],
  ["I","Investigate","Analyze supporting and opposing metrics."],
  ["G","Gauge","Assess persistence of evidence."],
  ["N","Narrative","Build a coherent explanation."],
  ["A","Assess","Highlight key risks and uncertainties."],
  ["L","Look Ahead","Surface what to monitor next."]
];

function MethodologyContent(){
  const [data,setData]=useState<MethodologyPayload|null>(null);
  const [reaction,setReaction]=useState<ReactionValidationPayload|null>(null);
  const [overview,setOverview]=useState<OverviewPayload|null>(null);
  const [error,setError]=useState<string|null>(null);
  useEffect(()=>{let alive=true;getMethodology().then(async m=>{const [r,o]=await Promise.all(["detector" in m?Promise.resolve(null):getReactionValidation().catch(()=>null),getOverview().catch(()=>null)]);return [m,r,o] as const;}).then(([m,r,o])=>{if(alive){setData(m);setReaction(r);setOverview(o);}}).catch((e:Error)=>alive&&setError(e.message));return()=>{alive=false;};},[]);
  if(error) return <div className="error-card"><h2>Unable to load Methodology</h2><p>{error}</p></div>;
  if(!data) return <div className="skeleton skeleton-card"/>;
  if("detector" in data) return <PilotMethodology data={data}/>;

  return <>
    <section className="page-header v2-page-header"><div><div className="eyebrow magenta">Transparency & Trust</div><h1>Methodology</h1><p>How SIGNAL detects unusual market behaviour, builds investigations, and communicates uncertainty.</p></div><div className="method-status-card v2-method-status"><span>STATUS</span><strong>{human(data.status)}</strong></div></section>

    <section className="card v2-framework-card"><div className="v2-card-head"><span className="eyebrow">The SIGNAL Framework</span><h3>From market signal to forward-looking monitoring</h3></div><div className="v2-framework-flow">{FRAMEWORK.map(([letter,title,text],i)=><div key={letter} className="v2-framework-step"><div className="v2-framework-icon">{letter}</div><strong>{title}</strong><p>{text}</p>{i<FRAMEWORK.length-1&&<span className="v2-framework-arrow">→</span>}</div>)}</div></section>

    <section className="v2-method-main-grid">
      <div className="v2-method-left">
        <section className="card v2-detection-logic"><div className="v2-card-head"><span className="eyebrow">Detection Logic</span><h3>Key components used to identify unusual market behavior</h3></div><div className="v2-detection-grid">
          <Logic title="Price Range / Sideways Detection" value={`Compression ≥ ${data.spot_gate.compression_score_min}`} text="Identifies periods where the stock trades in a tighter range relative to its historical baseline." />
          <Logic title="Relative Activity" value={`Activity ≥ ${data.spot_gate.activity_score_min}`} text="Measures whether trading activity is abnormally elevated relative to the detector baseline." />
          <Logic title="Turnover + Core Activity" value={`≥ ${formatNumber(data.spot_gate.core_relative_min,2)}×`} text={`At least ${data.spot_gate.minimum_core_metrics} core metrics must clear the relative threshold for a hard Spot.`}/>
          <Logic title="Persistence" value={`${data.persistence_and_lifecycle.established_support_sessions_in_last_5_min}/5 sessions`} text="Tracks whether unusual behaviour remains supported across multiple sessions." />
        </div></section>

        <section className="card v2-confidence-method"><div className="v2-card-head"><span className="eyebrow">Evidence Confidence</span><h3>A composite consistency score—not a price probability</h3></div><div className="v2-confidence-method-grid"><div className="v2-confidence-big"><strong>79</strong><span>/100 example</span><small>Evidence Confidence</small></div><div className="v2-confidence-bars"><Weight label="Activity" value={30}/><Weight label="Compression" value={25}/><Weight label="Persistence" value={20}/><Weight label="Participation" value={15}/><Weight label="Flow" value={10}/></div></div><div className="v2-method-warning">Evidence Confidence is not a prediction of future price movement. It reflects consistency and support inside an active investigation.</div></section>

        <section className="card v2-how-to-read"><div className="v2-card-head"><span className="eyebrow">How to Read SIGNAL Pages</span><h3>Each page owns one question</h3></div><div className="v2-read-grid"><Read title="Summary" text="What is happening? Hypothesis, confidence, 5W+1H, evidence, look ahead."/><Read title="Market Activity" text="Show the trading data: price, transactions, turnover, average trade value."/><Read title="Context" text="What may explain it? Research group, market breadth, fundamentals/events/news when available."/><Read title="History" text="How has it evolved? Prior sessions, episodes, and point-in-time evidence."/><Read title="Watchlist" text="What should I keep monitoring? Investigation state and recent signal changes."/></div></section>
      </div>

      <aside className="v2-method-right">
        <section className="card v2-key-terms"><div className="v2-card-head"><span className="eyebrow">Key Terms</span><h3>Definitions</h3></div><Term title="Relative Activity" text="Trading activity relative to a historical baseline; in this build relative turnover is a primary visible proxy."/><Term title="Price Range" text="Current 5-session price range used as part of compression evidence."/><Term title="Turnover" text="Total traded value over a session when actual raw data is available; otherwise relative turnover is shown."/><Term title="Average Trade Value" text="Transaction value divided by transaction count when actual raw data is available."/><Term title="Persistence" text="How often criteria remain satisfied within a recent session window, e.g. 4/5 sessions."/><Term title="Context Specificity" text="How distinct ticker-level activity is from same-day market and research-peer activity."/></section>

        <section className="card v2-guardrails"><div className="v2-card-head"><span className="eyebrow">Interpretation Guardrails</span><h3>What SIGNAL does not claim</h3></div><ol>{data.important_limitations.slice(0,6).map(x=><li key={x}>{x}</li>)}</ol></section>

        {overview?.spotlight && <section className="card v2-example-snapshot"><div className="v2-card-head"><span className="eyebrow">Example Investigation Snapshot</span><h3>{overview.spotlight.symbol}</h3></div><div className="v2-example-meta"><StatusBadge state={overview.spotlight.state}/><span>{human(overview.spotlight.peer_group??"Unmapped")}</span></div><div className="v2-example-grid"><Example label="Relative activity" value={overview.spotlight.relative_turnover==null?"—":`${formatNumber(overview.spotlight.relative_turnover,2)}×`}/><Example label="Price range" value={overview.spotlight.current_5d_range_pct==null?"—":`${formatNumber(overview.spotlight.current_5d_range_pct,2)}%`}/><Example label="Persistence" value={`${overview.spotlight.persistence_hits}/${overview.spotlight.persistence_window}`}/><Example label="Evidence Confidence" value={overview.spotlight.evidence_confidence==null?"—":`${formatNumber(overview.spotlight.evidence_confidence,0)}/100`}/></div></section>}
      </aside>
    </section>

    {reaction && <HistoricalReactionProfile data={reaction} title="Reaction Validation Profile"/>}

    <section className="card v2-calibration-card"><div className="v2-card-head"><span className="eyebrow">Calibration Review</span><h3>Why the current thresholds were retained</h3></div><div className="review-findings-grid">{Object.entries(data.review_findings).map(([k,v])=><div key={k}><strong>{human(k)}</strong><p>{v}</p></div>)}</div></section>
  </>;
}

function Logic({title,value,text}:{title:string;value:string;text:string}){return <div className="v2-logic-card"><span className="v2-logic-icon">◫</span><h4>{title}</h4><strong>{value}</strong><p>{text}</p></div>;}
function Weight({label,value}:{label:string;value:number}){return <div className="v2-weight-row"><div><span>{label}</span><strong>{value}%</strong></div><div><span style={{width:`${value/30*100}%`}}/></div></div>;}
function Term({title,text}:{title:string;text:string}){return <div className="v2-term"><strong>{title}</strong><p>{text}</p></div>;}
function Read({title,text}:{title:string;text:string}){return <div><strong>{title}</strong><p>{text}</p></div>;}
function Example({label,value}:{label:string;value:string}){return <div><span>{label}</span><strong>{value}</strong></div>;}
function human(v:string){return v.replaceAll("_"," ").toLowerCase().replace(/\b\w/g,c=>c.toUpperCase());}

export function MethodologyPage(){return <div className="ov-demo ov-variant-4 su-demo me-demo"><div className="ov-shell su-shell"><header className="ov-glass-nav"><NavbarGlass/><Link className="ov-brand" to="/"><span className="ov-logo"><img src="/signal-logo-generated.png" alt=""/></span>SIGNAL</Link><nav aria-label="Navigasi utama"><Link to="/">Overview</Link><Link to="/investigations">Investigations</Link><Link to="/watchlist">Watchlist</Link><Link className="selected" to="/methodology">Methodology</Link></nav><span className="ov-user">AS</span></header><main><MethodologyContent/></main><footer className="su-footer"><strong>SIGNAL</strong><span>Look closer. Think clearer.</span><Link to="/investigations">Explore investigations ↗</Link></footer></div></div>;}
