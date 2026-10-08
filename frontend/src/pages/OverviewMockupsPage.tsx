import {NavbarGlass} from "../components/NavbarGlass";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "../lib/conceptNavigation";
import { getActivity, getHistory, getInvestigations, getOverview } from "../lib/api";
import type { ActivityPayload, EpisodeSummary, InvestigationListItem, OverviewPayload } from "../types";
import { OverviewPriceChart } from "../components/OverviewPriceChart";
import { EpisodeMiniChart } from "../components/EpisodeMiniChart";
import { companyName } from "../lib/companies";
import "../overview-mockups.css";

const concepts = ["Editorial", "Research desk", "Focus", "Gallery", "Night terminal"];
type Recent = EpisodeSummary & { symbol: string; company: string };
const fmt = (n: number | null | undefined, decimals=0) => n == null ? "—" : n.toLocaleString("id-ID", { maximumFractionDigits: decimals });
const date = (d: string) => new Date(d+"T00:00:00").toLocaleDateString("id-ID", {day:"numeric",month:"short"});
export function OverviewMockupsPage() {
  const [params,setParams] = useSearchParams();
  const raw = Number(params.get("variant") ?? 1); const variant = raw >= 1 && raw <= 5 && Number.isInteger(raw) ? raw : 1;
  const [overview,setOverview] = useState<OverviewPayload>();
  const [spot,setSpot] = useState<InvestigationListItem>();
  const [activity,setActivity] = useState<ActivityPayload>();
  const [recent,setRecent] = useState<Recent[]>([]);
  const [cardActivity,setCardActivity] = useState<Record<string,ActivityPayload>>({});
  const [cardErrors,setCardErrors] = useState<Record<string,boolean>>({});
  const cardCache = useRef(new Map<string,Promise<ActivityPayload>>());
  const [query,setQuery] = useState("");
  const [error,setError] = useState("");
  const [historyError,setHistoryError] = useState(false);
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [o,explorer] = await Promise.all([getOverview(),getInvestigations()]);
        const s = o.spotlight ? explorer.items.find(i=>i.symbol===o.spotlight!.symbol) ?? o.spotlight : undefined;
        const [a,histories] = await Promise.all([s ? getActivity(s.symbol) : Promise.resolve(undefined), Promise.allSettled(explorer.items.map(async i => ({ item:i, history:await getHistory(i.symbol) })))]);
        if(cancelled) return;
        setOverview(o); setSpot(s); setActivity(a);
        setHistoryError(histories.some(h=>h.status==="rejected"));
        setRecent(histories.flatMap(h=>h.status === "fulfilled" ? h.value.history.episodes.filter(e=>!(h.value.item.symbol===s?.symbol && !e.closed)).map(e=>({...e,symbol:h.value.item.symbol,company:companyName(h.value.item.symbol,h.value.item.company_name)})) : []).sort((a,b)=>b.opened_at.localeCompare(a.opened_at)||a.symbol.localeCompare(b.symbol)));
      } catch { if(!cancelled) setError("Overview belum dapat dimuat. Periksa apakah server lokal sedang berjalan."); }
    }
    void load(); return ()=>{cancelled=true;};
  },[]);
  const latest = recent.filter(r=>`${r.symbol} ${r.company}`.toLowerCase().includes(query.toLowerCase())).slice(0,variant===4 ? 8 : 6);
  const chartSymbols = [...new Set(latest.map(r=>r.symbol))].sort().join(",");
  useEffect(()=>{
    if(variant !== 4 || !chartSymbols) return;
    let cancelled = false;
    for(const symbol of chartSymbols.split(",")) {
      if(!cardCache.current.has(symbol)) cardCache.current.set(symbol,getActivity(symbol));
      cardCache.current.get(symbol)!.then(payload=>{if(!cancelled) setCardActivity(prev=>({...prev,[symbol]:payload}));}).catch(()=>{if(!cancelled) setCardErrors(prev=>({...prev,[symbol]:true}));});
    }
    return ()=>{cancelled=true;};
  },[variant,chartSymbols]);
  const last = activity?.series.filter(p=>p.close != null).at(-1);
  const hero = <article className="ov-spot ov-panel">
    <div className="ov-kicker"><span className="ov-dot" /> Spotlight investigation <span className="ov-state">{spot?.state ?? "—"}</span></div>
    <div className="ov-spot-heading"><div><h2>{spot?.symbol ?? "—"}</h2><p>{spot ? companyName(spot.symbol,spot.company_name) : "—"}</p></div><div className="ov-price"><span>Harga terakhir</span><strong>Rp {fmt(last?.close)}</strong>{spot?.daily_change_pct != null && <small className={spot.daily_change_pct < 0 ? "negative":"positive"}>{spot.daily_change_pct>0?"+":""}{fmt(spot.daily_change_pct,2)}%</small>}</div></div>
    <p className="ov-spot-copy">Aktivitas yang patut diperhatikan. Telusuri pergerakan harga, bukti, dan broker di balik investigasi ini.</p>
    <div className="ov-metrics"><div><span>Evidence confidence</span><strong>{fmt(spot?.evidence_confidence,1)}<em>/100</em></strong></div><div><span>Relative turnover</span><strong>{fmt(spot?.relative_turnover,2)}<em>×</em></strong></div><div><span>Range 5 sesi</span><strong>{fmt(spot?.current_5d_range_pct,2)}<em>%</em></strong></div></div>
    <div className="ov-spot-actions"><Link className="ov-primary" to={`/investigations/${spot?.symbol ?? "BBCA"}/summary`}>Buka investigasi <span>↗</span></Link><Link className="ov-secondary" to={`/investigations/${spot?.symbol ?? "BBCA"}/brokers`}>Lihat broker →</Link></div>
  </article>;
  const chart = activity && spot ? <div className="ov-price-panel ov-panel"><OverviewPriceChart points={activity.series} symbol={spot.symbol} dark={variant===5 || variant===4} graphiteIce={variant===4}/></div> : null;
  const list = <section className="ov-latest"><div className="ov-section-heading"><div><span className="ov-kicker">DISCOVER</span><h2>Latest investigations</h2></div><Link to="/investigations">Semua investigasi ↗</Link></div>
    {historyError && <p role="alert">Sebagian investigasi belum dapat dimuat.</p>}
    <div className="ov-recent-list">{latest.map((r,index)=><Link to={`/investigations/${r.symbol}/history`} className="ov-recent ov-panel" key={r.investigation_id}>
      <span className="ov-rank">{String(index+1).padStart(2,"0")}</span><span className="ov-stock-avatar">{r.symbol.slice(0,2)}</span><div className="ov-recent-name"><strong>{r.symbol}</strong><span>{r.company}</span></div>
      {variant===4 && <EpisodeMiniChart points={cardActivity[r.symbol]?.series} episode={r} symbol={r.symbol} loading={!cardActivity[r.symbol] && !cardErrors[r.symbol]} failed={cardErrors[r.symbol]}/> }
      <div className="ov-episode"><span>{date(r.opened_at)}{r.closed_at ? ` – ${date(r.closed_at)}` : ""}</span><small className="ov-history-tag">{r.closed ? "Selesai" : "Berlangsung"}</small></div><div className="ov-recent-evidence"><small>Peak confidence</small><strong>{fmt(r.max_evidence_confidence,1)}<em>/100</em></strong></div><span className="ov-arrow">↗</span>
    </Link>)}</div>{latest.length===0 && <p>Tidak ada investigasi yang cocok.</p>}
  </section>;
  return <div className={`ov-demo ov-variant-${variant}`}>
    <div className="ov-reviewbar"><span>OVERVIEW CONCEPTS</span><div>{concepts.map((c,i)=><button key={c} aria-pressed={variant===i+1} onClick={()=>setParams({variant:String(i+1)})}>{String(i+1).padStart(2,"0")} <span>{c}</span></button>)}</div></div>
    <div className="ov-orb ov-orb-one"/><div className="ov-orb ov-orb-two"/>
    <div className="ov-shell"><header className="ov-glass-nav"><NavbarGlass/><Link to="/design/overview" className="ov-brand"><span className="ov-logo"><img src="/signal-logo-generated.png" alt="" /></span>SIGNAL</Link><nav aria-label="Navigasi utama"><Link className="selected" to={`/design/overview?variant=${variant}`}>Overview</Link><Link to="/investigations">Investigations</Link><Link to="/watchlist">Watchlist</Link><Link to="/methodology">Methodology</Link></nav><label className="ov-search"><span>⌕</span><input aria-label="Cari investigasi terbaru" placeholder="Cari saham atau perusahaan" value={query} onChange={e=>setQuery(e.target.value)}/></label><span className="ov-user" aria-label="Profil Aldo">AS</span></header>
    <main>{error ? <p className="ov-panel" role="alert">{error}</p> : !overview ? <p className="ov-panel" role="status">Memuat investigasi…</p> : <>
      <div className="ov-intro"><div><span className="ov-kicker">YOUR RESEARCH STARTS HERE</span><h1>{variant===3 ? "One signal. A closer look." : variant===5 ? "Read the market differently." : "See the story behind the stock."}</h1><p>Temukan investigasi menarik. Lihat bukti. Bangun perspektif Anda.</p></div><Link className="ov-explore" to="/investigations">Explore investigations ↗</Link></div>
      {variant===1 && <><div className="ov-feature-grid">{hero}{chart}</div>{list}</>}
      {variant===2 && <div className="ov-desk"><div className="ov-desk-main">{chart}{list}</div><aside>{hero}<div className="ov-desk-note ov-panel"><span className="ov-kicker">NEXT STEP</span><h3>Follow the evidence.</h3><p>Lihat aktivitas pasar dan broker untuk memahami cerita yang lebih lengkap.</p><Link to={`/investigations/${spot?.symbol}/activity`}>Market activity ↗</Link></div></aside></div>}
      {variant===3 && <><div className="ov-focus ov-panel">{hero}{chart}</div>{list}</>}
      {variant===4 && <><div className="ov-gallery-feature">{hero}{chart}</div>{list}</>}
      {variant===5 && <><div className="ov-terminal-title"><span>RESEARCH / SPOTLIGHT</span><span>PRICE · ACTIVITY · EVIDENCE</span></div><div className="ov-feature-grid">{hero}{chart}</div>{list}</>}
    </>}</main><footer className="ov-footer"><strong>SIGNAL</strong><span>Look closer. Think clearer.</span><Link to="/methodology">Methodology ↗</Link></footer></div>
  </div>;
}
