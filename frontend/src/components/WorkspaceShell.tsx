import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getInvestigation } from "../lib/api";
import type { InvestigationDetail } from "../types";
import { WatchlistButton } from "./WatchlistButton";
import { formatNumber } from "../lib/format";
import { companyName, humanGroup } from "../lib/companies";

export function WorkspaceShell(){
  const {symbol=""}=useParams(); const navigate=useNavigate();
  const [detail,setDetail]=useState<InvestigationDetail|null>(null);
  useEffect(()=>{let alive=true;getInvestigation(symbol).then(p=>alive&&setDetail(p)).catch(()=>alive&&setDetail(null));return()=>{alive=false;};},[symbol]);
  return <>
    <section className="v23-workspace-head">
      <button className="v23-back" onClick={()=>navigate('/investigations')}>← Back to Investigations</button>
      <div className="v23-workspace-mainrow">
        <div className="v23-workspace-identity">
          <div className="v23-symbol-lockup"><h1>{symbol.toUpperCase()}</h1><span>{companyName(symbol,detail?.identity.company_name)}</span>{detail?.identity.peer_group&&<><i>{humanGroup(detail.identity.peer_group)}</i><i>IDX30</i></>}</div>
        </div>
        <nav className="v23-workspace-tabs" aria-label="Ticker workspace">
          <Tab to="summary">Summary</Tab><Tab to="activity">Market Activity</Tab><Tab to="brokers">Broker</Tab><Tab to="context">Context</Tab><Tab to="history">History</Tab>
        </nav>
        <div className="v23-workspace-actions"><div><span>Last Price (IDR)</span><strong>{detail?.metrics.close==null?'—':formatNumber(detail.metrics.close,0)}</strong></div><WatchlistButton symbol={symbol}/></div>
      </div>
    </section>
    <Outlet/>
  </>;
}
function Tab({to,children}:{to:string;children:React.ReactNode}){return <NavLink to={to} className={({isActive})=>isActive?'v23-tab active':'v23-tab'}>{children}</NavLink>}
