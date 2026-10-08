import {useEffect,useRef,useState} from 'react';
import {createChart,LineSeries,ColorType,CrosshairMode} from 'lightweight-charts';
import type {Time} from 'lightweight-charts';
import type {ContextPayload} from '../types';

const num=(v:number|null|undefined,d=2)=>v==null?'—':v.toLocaleString('id-ID',{maximumFractionDigits:d});
const money=(v:number|null|undefined)=>v==null?'—':Math.abs(v)>=1e12?`Rp ${num(v/1e12)} T`:Math.abs(v)>=1e9?`Rp ${num(v/1e9)} B`:`Rp ${num(v)}`;
function safeUrl(value:string|null|undefined){try{const u=new URL(value??'');return ['http:','https:'].includes(u.protocol)?u.href:null;}catch{return null;}}
export function SnapshotFacts({context}:{context:ContextPayload}){
 const s=context.company_snapshot;if(!s)return null;
 const website=safeUrl(s.website?.startsWith('http')?s.website:`https://${s.website??''}`);
 return <div className="ct-snapshot"><div className="ct-snapshot-head"><strong>Company snapshot</strong><time>{s.price_date??s.captured_at}</time></div><dl><div><dt>Sektor</dt><dd>{s.sector??'—'}</dd></div><div><dt>Industri</dt><dd>{s.industry??'—'}</dd></div><div><dt>Market cap snapshot</dt><dd>{money(s.market_cap)}</dd></div></dl><p className="ct-period">Laporan tahunan {s.annual_year??'—'} · Valuasi {s.valuation_year??'—'}</p><div className="ct-fundamentals">{s.metrics.map(m=><div key={m.label}><span>{m.label}</span><strong>{m.value}</strong></div>)}</div>{website&&<a className="ct-source-link" href={website} target="_blank" rel="noreferrer">Website perusahaan ↗</a>}</div>;
}
function MarketChart({points}:{points:NonNullable<ContextPayload['market_history']>}){
 const host=useRef<HTMLDivElement>(null);const [legend,setLegend]=useState('');
 useEffect(()=>{if(!host.current)return;
 const last=points.at(-1);const initial=last?`${last.date} · IHSG ${num(last.ihsg)}`:'';setLegend(initial);
 const chart=createChart(host.current,{autoSize:true,height:200,layout:{background:{type:ColorType.Solid,color:'transparent'},textColor:'#b8c5d6',attributionLogo:true},grid:{vertLines:{visible:false},horzLines:{color:'#3c4a5c'}},crosshair:{mode:CrosshairMode.Normal},rightPriceScale:{borderVisible:false},timeScale:{borderVisible:false},handleScroll:{mouseWheel:true,pressedMouseMove:true,vertTouchDrag:false},handleScale:{mouseWheel:true,pinch:true}});
 const line=chart.addSeries(LineSeries,{color:'#67e8f9',lineWidth:2,priceFormat:{type:'price',precision:2,minMove:.01}});
 line.setData(points.filter(p=>p.ihsg!=null).map(p=>({time:p.date as Time,value:p.ihsg!})));
 chart.subscribeCrosshairMove(e=>{const bar=e.seriesData.get(line);setLegend(e.time&&bar&&'value' in bar?`${String(e.time)} · IHSG ${num(bar.value)}`:initial);});chart.timeScale().fitContent();return()=>chart.remove();},[points]);
 return <div className="ct-index-chart"><div role="status" className="ct-period">{legend}</div><div ref={host} style={{height:200}} aria-label="Grafik IHSG interaktif"/></div>;
}
export function ContextMarket({context}:{context:ContextPayload}){
 const rows=context.market_history??[];const first=rows[0],last=rows.at(-1);const change=first?.ihsg&&last?.ihsg!=null?(last.ihsg/first.ihsg-1)*100:null;
 return <section className="su-panel"><div className="su-panel-head"><h2>Market context</h2><span>Apr–Sep 2026</span></div>{rows.length?<><div className="ct-market-values"><div><span>IHSG · {last?.date}</span><strong>{num(last?.ihsg)}</strong></div><div><span>Perubahan periode</span><strong className={change!=null&&change<0?'ct-negative':'ct-positive'}>{change!=null&&change>0?'+':''}{num(change)}%</strong></div><div><span>Kapitalisasi IDX</span><strong>{money(last?.market_cap)}</strong></div></div><MarketChart points={rows}/></>:<p className="ct-empty">Perbandingan pasar belum tersedia.</p>}</section>;
}
export function ContextPeers({context,choose}:{context:ContextPayload;choose:(s:string)=>void}){
 const rows=context.fundamental_peers??[];
 return <section className="su-panel ct-peers"><div className="su-panel-head"><h2>Peer comparison</h2><span>Snapshot {context.company_snapshot?.price_date??'—'}</span></div>{rows.length?<div className="ct-table ct-peer-scroll"><table><thead><tr><th>Stock</th><th>Market cap</th><th>P/E TTM</th><th>P/B</th><th>Revenue</th></tr></thead><tbody>{rows.map(r=><tr key={r.symbol}><td>{r.in_universe?<button onClick={()=>choose(r.symbol)}>{r.symbol}</button>:<strong>{r.symbol}</strong>}<small>{r.name}</small></td><td>{money(r.market_cap)}</td><td>{num(r.pe)}×</td><td>{num(r.pb)}×</td><td>{money(r.revenue)}<small>FY {r.year??'—'}</small></td></tr>)}</tbody></table></div>:<p className="ct-empty">Perbandingan saham sekelompok belum tersedia.</p>}</section>;
}
export function ContextEvents({context}:{context:ContextPayload}){
 const rows=context.corporate_events??[];
 return <section className="su-panel ct-events"><div className="su-panel-head"><h2>Corporate events</h2><span>{rows.length} · Apr–Sep 2026</span></div>{rows.length?<div className="ct-list">{rows.map((r,i)=><article key={`${r.date}-${i}`}><time>{r.date}</time><strong>{r.type}</strong>{r.detail.length>240?<details><summary>{r.detail.slice(0,180)}…</summary><p>{r.detail}</p></details>:<p>{r.detail||'Detail belum tersedia.'}</p>}</article>)}</div>:<p className="ct-empty">Tidak ada aksi korporasi tercatat pada periode ini.</p>}</section>;
}
export function ContextNews({context}:{context:ContextPayload}){
 const [q,setQ]=useState(''),[page,setPage]=useState(0);const rows=(context.relevant_news??[]).filter(n=>`${n.title??''} ${(n.tags??[]).join(' ')}`.toLowerCase().includes(q.toLowerCase()));
 const pageCount=Math.max(1,Math.ceil(rows.length/12));const active=Math.min(page,pageCount-1);const shown=rows.slice(active*12,(active+1)*12);
 return <section className="su-panel ct-news"><div className="su-panel-head"><h2>Related news</h2><span>{rows.length} · Apr–Sep 2026</span></div><input className="ct-news-search" aria-label="Cari berita" placeholder="Cari judul atau topik…" value={q} onChange={e=>{setQ(e.target.value);setPage(0);}}/>{shown.length?<div className="ct-list">{shown.map((n,i)=>{const url=safeUrl(n.source);let domain='';if(url)domain=new URL(url).hostname.replace(/^www\./,'');return <article key={`${n.timestamp}-${i}`}><time>{n.timestamp.slice(0,10)}</time><strong>{url?<a href={url} target="_blank" rel="noreferrer">{n.title??'Artikel'} ↗</a>:n.title??'—'}</strong><p>{domain}{n.tags?.length?` · ${n.tags.slice(0,4).join(' · ')}`:''}</p></article>;})}</div>:<p className="ct-empty">Tidak ada berita yang cocok.</p>}<div className="ct-pagination"><button disabled={active===0} onClick={()=>setPage(active-1)}>← Sebelumnya</button><span>{active+1} / {pageCount}</span><button disabled={active>=pageCount-1} onClick={()=>setPage(active+1)}>Berikutnya →</button></div></section>;
}
