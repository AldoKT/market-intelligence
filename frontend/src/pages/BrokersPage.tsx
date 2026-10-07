import {BrokerNetChart} from "../components/BrokerNetChart";
import {useEffect,useMemo,useState} from 'react';
import {useParams} from 'react-router-dom';
import {getBrokerIndex,getBrokerSession,getBrokerEpisode,getBrokerHistory} from '../lib/api';
import type {BrokerIndex,BrokerPayload,BrokerRow,BrokerHistory} from '../lib/brokerTypes';
import {filterBrokers,brokerQualityLabel,observationLabel,type BrokerSort} from '../lib/brokers';
import {formatDate,formatNumber} from '../lib/format';

export function BrokersPage(){const {symbol=''}=useParams();return <BrokerWorkspace key={symbol} symbol={symbol}/>;}
function BrokerWorkspace({symbol}:{symbol:string}){
 const [index,setIndex]=useState<BrokerIndex|null>(null),[data,setData]=useState<BrokerPayload|null>(null);
 const [mode,setMode]=useState<'session'|'episode'>('session'),[day,setDay]=useState(''),[episode,setEpisode]=useState('');
 const [error,setError]=useState(''),[query,setQuery]=useState(''),[side,setSide]=useState('ALL');
 const [sort,setSort]=useState<BrokerSort>('gross_value_idr'),[descending,setDescending]=useState(true);
 const [selected,setSelected]=useState<string|null>(null),[history,setHistory]=useState<BrokerHistory|null>(null),[historyError,setHistoryError]=useState('');
 useEffect(()=>{let alive=true;getBrokerIndex(symbol).then(value=>{if(alive){setIndex(value);setDay(value.default_date??'');setEpisode(value.episodes.at(-1)?.investigation_id??'');}}).catch((e:Error)=>alive&&setError(e.message));return()=>{alive=false;};},[symbol]);
 useEffect(()=>{if(!index||(mode==='session'?!day:!episode))return;let alive=true;setData(null);setError('');setSelected(null);setHistory(null);
  const request=mode==='session'?getBrokerSession(symbol,day):getBrokerEpisode(symbol,episode);
  request.then(value=>alive&&setData(value)).catch((e:Error)=>alive&&setError(e.message));return()=>{alive=false;};
 },[symbol,index,mode,day,episode]);
 useEffect(()=>{setHistory(null);setHistoryError('');if(!selected||!data)return;let alive=true;
  if(mode==='episode'){setHistory(data.broker_histories?.find(h=>h.broker_code===selected)??null);return;}
  getBrokerHistory(symbol,selected,day).then(value=>alive&&setHistory(value)).catch((e:Error)=>alive&&setHistoryError(e.message));return()=>{alive=false;};
 },[selected,data,mode,symbol,day]);
 const rows=useMemo(()=>filterBrokers(data?.brokers??[],query,side,sort,descending),[data,query,side,sort,descending]);
 const broker=data?.brokers.find(r=>r.broker_code===selected);
 const badDates=data?.quality_by_session?Object.entries(data.quality_by_session).filter(([,q])=>q.status!=='RECONCILED_RESEARCH_CANDIDATE'):[];
 const scopeDate=mode==='session'?day:`${data?.start??''} — ${data?.last_observed_date??''}`;
 return <section className="workspace-page broker-page">
  <div className="broker-heading"><div><span className="broker-eyebrow">PHASE 2 · BROKER ACTIVITY</span><h2>Broker</h2><p>Seluruh aktivitas beli/jual yang dikembalikan sumber, dengan riwayat per sesi dan episode.</p></div>{index&&<span className="broker-date-badge">Data tersedia s.d. {formatDate(index.as_of)}</span>}</div>
  {index&&<aside className="broker-snapshot-note">Harga dan status di header SIGNAL memakai snapshot {formatDate(index.signal_snapshot)}. Analisis broker di bawah memakai periode yang dipilih.</aside>}
  {index&&<div className="card broker-controls"><div className="broker-mode" aria-label="Mode analisis"><button className={mode==='session'?'active':''} onClick={()=>setMode('session')}>Per sesi</button><button className={mode==='episode'?'active':''} onClick={()=>setMode('episode')} disabled={!index.episodes.length}>Per episode SIGNAL</button></div>
   {mode==='session'?<label>Tanggal sesi<select aria-label="Tanggal sesi" value={day} onChange={e=>setDay(e.target.value)}><option value="" disabled>Pilih tanggal</option>{[...index.dates].reverse().map(d=><option key={d} value={d}>{formatDate(d)}{d===index.signal_snapshot?' · snapshot SIGNAL':''}</option>)}</select></label>:<label>Episode SIGNAL<select aria-label="Episode SIGNAL" value={episode} onChange={e=>setEpisode(e.target.value)}>{index.episodes.map(e=><option key={e.investigation_id} value={e.investigation_id}>{formatDate(e.start)} — {formatDate(e.last_observed_date)} · {stateLabel(e.last_state)}</option>)}</select></label>}
  </div>}
  {error&&<div className="error-card" role="alert"><h3>Data Broker belum dapat dimuat</h3><p>{error}</p><p>Pastikan backend memakai profil JSON pilot dan data broker lokal tersedia.</p></div>}
  {index&&mode==='session'&&!day&&<p className="broker-empty">Snapshot SIGNAL belum tersedia sebagai sesi broker. Pilih tanggal sesi untuk melanjutkan.</p>}
  {!error&&!data&&(!index||(mode==='session'?Boolean(day):Boolean(episode)))&&<div className="skeleton skeleton-card" aria-label="Memuat data broker"/>}
  {data&&<>
   <div className="broker-scope"><strong>{mode==='session'?'Sesi':'Episode'} {scopeDate}</strong><span>{stateLabel(mode==='session'?data.signal_context?.lifecycle_state_v2:data.last_state)}</span></div>
   {data.quality&&<aside className={`broker-quality ${data.quality.status==='RECONCILED_RESEARCH_CANDIDATE'?'':'warning'}`} role="note"><strong>{brokerQualityLabel(data.quality.status)}</strong>{data.quality.status==='VOLUME_SCOPE_MISMATCH'&&<span>Broker: {formatNumber(data.quality.broker_volume_shares,0)} shares · harian: {formatNumber(data.quality.daily_volume_shares,0)} shares. Baris tetap ditampilkan dengan keterangan.</span>}</aside>}
   {mode==='episode'&&<aside className={`broker-quality ${badDates.length?'warning':''}`} role="note">{badDates.length?`${badDates.length} sesi bermasalah; nilai agregat hanya mencakup baris yang tersedia. Sesi bermasalah memutus riwayat berurutan.`:'Seluruh sesi episode cocok dengan volume harian; kelengkapan sumber belum diverifikasi.'}</aside>}
   <div className="broker-kpis"><Metric label="Broker tercatat" value={data.brokers.length?String(data.brokers.length):"—"}/><Metric label="Nilai beli total" value={data.brokers.length?money(data.summary.totals.bval):"—"}/><Metric label="Nilai jual total" value={data.brokers.length?money(data.summary.totals.sval):"—"}/><Metric label="Porsi beli 5 broker terbesar" value={percent(data.summary.top5_gross_buy_share_pct)}/></div>
   <div className="broker-leaders"><Leaders title="Net buy terbesar" codes={data.summary.top5_net_buy_codes} rows={data.brokers} onSelect={setSelected}/><Leaders title="Net sell terbesar" codes={data.summary.top5_net_sell_codes} rows={data.brokers} onSelect={setSelected}/></div>
   <article className="card broker-table-card"><div className="broker-table-title"><div><h3>Semua broker buy / sell</h3><p>{rows.length} dari {data.brokers.length} broker · termasuk net nol. Ringkasan di atas memakai daftar lengkap.</p></div></div>
    <div className="broker-filters"><label>Cari broker<input aria-label="Cari broker" placeholder="Kode atau nama broker" value={query} onChange={e=>setQuery(e.target.value)}/></label><label>Arah net<select aria-label="Arah net" value={side} onChange={e=>setSide(e.target.value)}><option value="ALL">Semua</option><option value="NET_BUY">Net buy</option><option value="NET_SELL">Net sell</option><option value="NET_FLAT">Net nol</option><option value="UNKNOWN">Belum diketahui</option></select></label><label>Urutkan<select aria-label="Urutkan broker" value={sort} onChange={e=>setSort(e.target.value as BrokerSort)}><option value="gross_value_idr">Nilai transaksi total</option><option value="bval">Nilai beli</option><option value="sval">Nilai jual</option><option value="nval">Net buy / sell</option><option value="broker_code">Kode broker</option></select></label><button className="broker-sort-direction" onClick={()=>setDescending(v=>!v)} aria-label="Balik urutan">{descending?'↓ Menurun':'↑ Menaik'}</button></div>
    <div className="broker-table-scroll"><table className="broker-table"><thead><tr><th>Broker</th><th>Beli (IDR)</th><th>Jual (IDR)</th><th>Net (IDR)</th><th>Lot beli</th><th>Lot jual</th><th>Net lot</th><th>Freq beli</th><th>Freq jual</th></tr></thead><tbody>{rows.map(r=><tr key={r.broker_code} className={selected===r.broker_code?'selected':''}><td><button className="broker-code" onClick={()=>setSelected(r.broker_code)}>{r.broker_code}</button><small>{r.broker_name??'Belum teridentifikasi'}</small></td><td>{formatNumber(r.bval,0)}</td><td>{formatNumber(r.sval,0)}</td><td className={signClass(r.nval)}>{formatNumber(r.nval,0)}</td><td>{formatNumber(r.blot,0)}</td><td>{formatNumber(r.slot,0)}</td><td className={signClass(r.nlot)}>{formatNumber(r.nlot,0)}</td><td>{formatNumber(r.bfreq,0)}</td><td>{formatNumber(r.sfreq,0)}</td></tr>)}</tbody></table></div>
    {!rows.length&&<p className="broker-empty">{!data.brokers.length?'Data broker sesi ini belum tersedia; tidak dianggap transaksi nol.':'Tidak ada broker yang cocok dengan pencarian atau filter.'}</p>}
   </article>
   {broker&&<article className="card broker-detail"><div className="broker-detail-title"><div><h3>{broker.broker_code} · {broker.broker_name??'Belum teridentifikasi'}</h3><p>{roleLabel(broker.net_role)} · {broker.registry_status==='MATCHED'?`Asal perusahaan broker: ${broker.broker_company_origin}`:'Kode belum cocok dengan registry; tidak diberi identitas rekaan.'}</p></div><button onClick={()=>setSelected(null)} aria-label="Tutup detail broker">Tutup ×</button></div>
    <div className="broker-kpis"><Metric label="Rata-rata beli / share" value={formatNumber(broker.weighted_buy_price_per_share,2)}/><Metric label="Rata-rata jual / share" value={formatNumber(broker.weighted_sell_price_per_share,2)}/><Metric label="Porsi nilai beli" value={percent(broker.buy_value_share_pct)}/><Metric label="Porsi nilai jual" value={percent(broker.sell_value_share_pct)}/></div>
    <h4>{mode==='episode'?'Riwayat sepanjang episode':'Riwayat hingga 20 sesi, berakhir pada tanggal yang dipilih'}</h4>
    {historyError&&<p role="alert">{historyError}</p>}
    {!history&&!historyError&&<p>Memuat riwayat…</p>}
    {history&&<><BrokerNetChart history={history}/>{mode==='episode'&&<p>Net buy berurutan: {history.max_consecutive_reconciled_net_buy_sessions} sesi · net sell berurutan: {history.max_consecutive_reconciled_net_sell_sessions} sesi · pergantian arah bersebelahan: {history.adjacent_net_buy_sell_switches}.</p>}<div className="broker-history-scroll"><table className="broker-table broker-history"><thead><tr><th>Tanggal</th><th>Observasi</th><th>Beli (IDR)</th><th>Jual (IDR)</th><th>Net (IDR)</th><th>Arah</th></tr></thead><tbody>{history.series.map(r=><tr key={r.date}><td>{formatDate(r.date)}</td><td>{observationLabel(r.observation)}{r.observation==='RETURNED'&&r.session_quality!=='RECONCILED_RESEARCH_CANDIDATE'&&<small>{brokerQualityLabel(r.session_quality??'')}</small>}</td><td>{formatNumber(r.bval,0)}</td><td>{formatNumber(r.sval,0)}</td><td className={signClass(r.nval)}>{formatNumber(r.nval,0)}</td><td>{roleLabel(r.net_role)}</td></tr>)}</tbody></table></div></>}
   </article>}
   <p className="broker-footnote">Semua broker berarti seluruh kode yang dikembalikan API, termasuk kode belum teridentifikasi. Lot dikonversi dengan 100 shares/lot. Harga rata-rata dihitung dari nilai ÷ shares; broker yang tidak muncul tetap unknown. Identitas broker tidak menunjukkan identitas investor atau membuktikan akumulasi.</p>
  </>}
 </section>;
}
function Metric({label,value}:{label:string;value:string}){return <div className="card broker-metric"><span>{label}</span><strong>{value}</strong></div>;}
function Leaders({title,codes,rows,onSelect}:{title:string;codes:string[];rows:BrokerRow[];onSelect:(code:string)=>void}){return <article className="card broker-leader"><h3>{title}</h3><div>{codes.map(code=>{const r=rows.find(r=>r.broker_code===code)!;return <button key={code} onClick={()=>onSelect(code)}><strong>{code}</strong><span className={signClass(r.nval)}>{money(r.nval)}</span></button>;})}{!codes.length&&<span>Belum ada data.</span>}</div></article>;}
function money(value:number|null){if(value==null)return "—";const a=Math.abs(value);return `IDR ${formatNumber(value/(a>=1e12?1e12:a>=1e9?1e9:a>=1e6?1e6:1),2)}${a>=1e12?' T':a>=1e9?' B':a>=1e6?' M':''}`;}
function percent(value:number|null){return value==null?'—':`${formatNumber(value,1)}%`;}
function signClass(value:number|null){return value==null?'':value>0?'pos':value<0?'neg':'';}
function roleLabel(value:string|null){return value==='NET_BUY'?'Net buy':value==='NET_SELL'?'Net sell':value==='NET_FLAT'?'Net nol':'Belum diketahui';}
function stateLabel(value:string|null|undefined){return value==='NO_INVESTIGATION'?'Tidak ada investigasi aktif':value==='CLOSED'?'Episode ditutup':value??'Status belum diketahui';}
