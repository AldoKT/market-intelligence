import { Link } from "react-router-dom";
import type { InvestigationListItem } from "../types";
import { StatusBadge } from "./StatusBadge";
import { formatNumber } from "../lib/format";
import { companyName } from "../lib/companies";

export function InvestigationTable({items,selectedSymbol,onSelect}:{items:InvestigationListItem[];selectedSymbol?:string|null;onSelect?:(item:InvestigationListItem)=>void}){
  if(!items.length)return <div className="v23-empty"><h3>No investigations match this view</h3><p>Adjust the current filters or search term.</p></div>;
  return <div className="v23-investigation-table-wrap"><table className="v23-investigation-table"><thead><tr><th>#</th><th>Ticker</th><th>Company</th><th>Pattern</th><th>Confidence</th><th>Last Price</th><th>1D Change</th><th>State</th><th>Persistence</th><th>Activity</th><th/></tr></thead><tbody>{items.map((item,i)=><tr key={item.symbol} className={selectedSymbol===item.symbol?'selected':''} onClick={()=>onSelect?.(item)}><td>{i+1}</td><td><Link to={`/investigations/${item.symbol}/summary`} onClick={e=>e.stopPropagation()}><strong>{item.symbol}</strong></Link></td><td><span className="company">{companyName(item.symbol,item.company_name)}</span></td><td><span className="v23-pattern">Sideways Accum.</span></td><td><span className="v23-score">{item.evidence_confidence==null?'—':formatNumber(item.evidence_confidence,0)}</span></td><td>{item.close==null?'—':formatNumber(item.close,0)}</td><td className={changeClass(item.daily_change_pct)}>{item.daily_change_pct==null?'—':`${item.daily_change_pct>=0?'+':''}${formatNumber(item.daily_change_pct,2)}%`}</td><td><StatusBadge state={item.state}/></td><td><span className="v23-persistence">{formatNumber(item.persistence_hits,0)}/{item.persistence_window}</span></td><td><ActivityBar value={item.relative_turnover}/></td><td><Link to={`/investigations/${item.symbol}/summary`} aria-label={`Buka detail ${item.symbol}`} onClick={e=>e.stopPropagation()}>Buka detail →</Link></td></tr>)}</tbody></table></div>
}
function ActivityBar({value}:{value:number|null}){const w=value==null?0:Math.min(100,(value/3)*100);return <div className="v23-activity-mini"><i style={{width:`${w}%`}}/><span>{value==null?'—':`${formatNumber(value,2)}x`}</span></div>}
function changeClass(v?:number|null){if(v==null||v===0)return'';return v>0?'pos':'neg'}
