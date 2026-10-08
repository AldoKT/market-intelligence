import {NavbarGlass} from "../components/NavbarGlass";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {companyName} from "../lib/companies";
import {withLatestPrice} from "../lib/pilot";
import "../overview-mockups.css";
import "../summary-mockups.css";
import "../watchlist-design.css";
import { getActivity, getInvestigations } from "../lib/api";
import type { ActivityPayload, InvestigationExplorerPayload } from "../types";
import { useWatchlist } from "../lib/watchlist";
import { MiniSparkline } from "../components/MiniSparkline";
import { StatusBadge } from "../components/StatusBadge";
import { formatNumber } from "../lib/format";

export function WatchlistPage(){
  const [data,setData]=useState<InvestigationExplorerPayload|null>(null);
  const [series,setSeries]=useState<Record<string,ActivityPayload>>({});
  const [filter,setFilter]=useState("ALL");
  const [compare,setCompare]=useState<string[]>([]);
  const [error,setError]=useState<string|null>(null);
  const watchlist=useWatchlist();
  const navigate=useNavigate();

  useEffect(()=>{let alive=true;getInvestigations().then(p=>alive&&setData(p)).catch((e:Error)=>alive&&setError(e.message));return()=>{alive=false;};},[]);
  const items=useMemo(()=>data?data.items.filter(i=>watchlist.symbols.includes(i.symbol)):[],[data,watchlist.symbols]);
  useEffect(()=>{let alive=true;if(!items.length){setSeries({});return;}Promise.all(items.map(i=>getActivity(i.symbol).then(a=>[i.symbol,a] as const).catch(()=>null))).then(rows=>{if(!alive)return;const next:Record<string,ActivityPayload>={};rows.forEach(r=>{if(r)next[r[0]]=r[1];});setSeries(next);});return()=>{alive=false;};},[items.map(i=>i.symbol).join(",")]);

  const filtered=items.filter(i=>filter==="ALL"?true:filter==="ACTIVE"?i.active:i.state===filter);
  const active=items.filter(i=>i.active).length;
  const established=items.filter(i=>i.state==="ESTABLISHED").length;
  const weakening=items.filter(i=>i.state==="WEAKENING").length;
  const groupCounts=useMemo(()=>{const m=new Map<string,number>();items.forEach(i=>{const g=i.peer_group??"Unmapped";m.set(g,(m.get(g)??0)+1);});return [...m.entries()].sort((a,b)=>b[1]-a[1]);},[items]);
  const visibleCompare=compare.filter(sym=>items.some(i=>i.symbol===sym));
  const displayItems=filtered.map(i=>series[i.symbol]?withLatestPrice(i,series[i.symbol]):i);
  const [addSymbol,setAddSymbol]=useState("");

  return <div className="ov-demo ov-variant-4 su-demo wl-demo"><div className="ov-shell su-shell"><header className="ov-glass-nav"><NavbarGlass/><Link to="/" className="ov-brand"><span className="ov-logo"><img src="/signal-logo-generated.png" alt=""/></span>SIGNAL</Link><nav aria-label="Navigasi utama"><Link to="/">Overview</Link><Link to="/investigations">Investigations</Link><Link className="selected" to="/watchlist">Watchlist</Link><Link to="/methodology">Methodology</Link></nav><span className="ov-user">AS</span></header><main>{error&&<p role="alert" className="su-panel">Watchlist belum dapat dimuat.</p>}

    <section className="page-header v2-page-header"><div><div className="ov-kicker">YOUR RESEARCH, IN ONE PLACE</div><h1>My Watchlist</h1><p>Your stocks. A closer watch.</p></div><div className="wl-add"><select aria-label="Pilih saham untuk watchlist" value={addSymbol} onChange={e=>setAddSymbol(e.target.value)}><option value="">Choose stock</option>{data?.items.filter(i=>!watchlist.has(i.symbol)).map(i=><option key={i.symbol} value={i.symbol}>{i.symbol}</option>)}</select><button disabled={!addSymbol} onClick={()=>{if(addSymbol&&!watchlist.has(addSymbol)){watchlist.toggle(addSymbol);setAddSymbol("");}}}>+ Add stock</button></div></section>

    <section className="v2-watchlist-tabs">{[["ALL","All"],["ACTIVE","Active"],["ESTABLISHED","Established"],["WEAKENING","Weakening"]].map(([v,l])=><button key={v} aria-pressed={filter===v} className={filter===v?"active":""} onClick={()=>setFilter(v)}>{l}</button>)}</section>

    <section className="v2-watchlist-kpis"><Kpi label="Total Stocks" value={items.length} helper=""/><Kpi label="Active Investigations" value={active} helper=""/><Kpi label="Established" value={established} helper=""/><Kpi label="Weakening" value={weakening} helper=""/></section>

    {!data&&!error?<p role="status">Memuat Watchlist…</p>:items.length ? <section className="v2-watchlist-main-grid">
      <article className="card v2-watchlist-table-card">
        <div className="v2-card-head v2-card-head-row"><div><span className="eyebrow">Watchlist Stocks</span><h3>Current signals</h3></div><span className="v2-table-note">Select up to two for comparison</span></div>
        <div className="v2-table-wrap"><table className="v2-data-table v2-watchlist-table"><thead><tr><th></th><th>Ticker</th><th>Close</th><th>1D change</th><th>Trend</th><th>Confidence</th><th>State</th><th>Persistence</th><th>Action</th></tr></thead><tbody>{displayItems.map(item=>{const a=series[item.symbol];return <tr key={item.symbol}><td><input type="checkbox" aria-label={"Bandingkan "+item.symbol} checked={visibleCompare.includes(item.symbol)} onChange={()=>toggleCompare(item.symbol,visibleCompare,setCompare)} /></td><td><strong>{item.symbol}</strong><small>{companyName(item.symbol,item.company_name)}</small></td><td>{item.close==null?"—":formatNumber(item.close,2)}</td><td><span className={changeClass(item.daily_change_pct)}>{item.daily_change_pct==null?"—":`${item.daily_change_pct>=0?"+":""}${formatNumber(item.daily_change_pct,2)}%`}</span></td><td><MiniSparkline values={a?.series.slice(-20).map(p=>p.close)??[]} width={90} height={28}/></td><td><strong>{item.evidence_confidence==null?"—":formatNumber(item.evidence_confidence,0)}</strong></td><td><StatusBadge state={item.state}/></td><td>{item.persistence_hits==null?"—":formatNumber(item.persistence_hits,0)+"/"+item.persistence_window}</td><td><button className="v2-row-action" onClick={()=>navigate(`/investigations/${item.symbol}/summary`)}>Open ↗</button><button className="wl-remove" aria-label={"Hapus "+item.symbol+" dari watchlist"} onClick={()=>watchlist.toggle(item.symbol)}>×</button></td></tr>;})}</tbody></table>{!filtered.length&&<p className="wl-filter-empty">No stocks match this filter.</p>}</div>
      </article>

      <aside className="v2-watchlist-side">
        <section className="card v2-sector-distribution"><div className="v2-card-head"><span className="eyebrow">Research Group Distribution</span><h3>Current concentration</h3></div><div className="v2-group-bars">{groupCounts.map(([g,n])=><div key={g}><span>{human(g)}</span><div><i style={{width:`${items.length?n/items.length*100:0}%`}}/></div><strong>{n}</strong></div>)}</div></section>
        <section className="card v2-recent-signal-updates"><div className="v2-card-head"><span className="eyebrow">Recent Signal Updates</span><h3>Lifecycle changes</h3></div><div>{items.slice().sort((a,b)=>b.last_updated.localeCompare(a.last_updated)).slice(0,6).map(i=><button key={i.symbol} onClick={()=>navigate(`/investigations/${i.symbol}/summary`)}><span><strong>{i.symbol}</strong><small>{human(i.state)}</small></span><StatusBadge state={i.state}/></button>)}</div></section>
      </aside>
    </section> : <section className="card v2-watchlist-empty"><div className="empty-state"><div className="empty-icon">☆</div><h3>Your monitoring list is empty</h3><p>Add tickers from Investigations. Keep the stocks you want to follow here.</p><button className="primary-button v2-primary-button" onClick={()=>navigate("/investigations")}>Browse Investigations</button></div></section>}

    {visibleCompare.length===2 && <section className="card v2-compare-panel"><div className="v2-card-head v2-card-head-row"><div><span className="eyebrow">Compare</span><h3>{visibleCompare[0]} vs {visibleCompare[1]}</h3></div><button className="v2-text-button" onClick={()=>setCompare([])}>Clear</button></div><div className="v2-compare-grid">{visibleCompare.map(sym=>{const item=items.find(i=>i.symbol===sym)!;return <div key={sym}><h3>{sym}</h3><Metric label="Confidence" value={item.evidence_confidence==null?"—":`${formatNumber(item.evidence_confidence,0)}/100`}/><Metric label="Relative activity" value={item.relative_turnover==null?"—":`${formatNumber(item.relative_turnover,2)}×`}/><Metric label="Persistence" value={item.persistence_hits==null?"—":`${formatNumber(item.persistence_hits,0)}/${item.persistence_window}`}/><Metric label="State" value={human(item.state)}/></div>;})}</div></section>}
  </main><footer className="su-footer"><strong>SIGNAL</strong><span>Look closer. Think clearer.</span><Link to="/investigations">Explore investigations ↗</Link></footer></div></div>;
}

function Kpi({label,value,helper}:{label:string;value:number;helper:string}){return <div className="card v2-watch-kpi"><span>{label}</span><strong>{value}</strong><small>{helper}</small></div>;}
function Metric({label,value}:{label:string;value:string}){return <div className="v2-compare-metric"><span>{label}</span><strong>{value}</strong></div>;}
function toggleCompare(sym:string,current:string[],set:(v:string[])=>void){if(current.includes(sym)){set(current.filter(x=>x!==sym));return;}if(current.length<2)set([...current,sym]);else set([current[1],sym]);}
function human(v:string){return v.replaceAll("_"," ").toLowerCase().replace(/\b\w/g,c=>c.toUpperCase());}
function changeClass(v?:number|null){if(v==null||v===0)return"v2-change-neutral";return v>0?"v2-change-positive":"v2-change-negative";}
