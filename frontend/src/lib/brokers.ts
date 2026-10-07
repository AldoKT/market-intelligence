import type {BrokerRow} from './brokerTypes';
export type BrokerSort='gross_value_idr'|'bval'|'sval'|'nval'|'broker_code';
export function filterBrokers(rows:BrokerRow[],query:string,side:string,sort:BrokerSort,descending:boolean){
 const q=query.trim().toLowerCase();
 const filtered=rows.filter(r=>(!q||`${r.broker_code} ${r.broker_name??''}`.toLowerCase().includes(q))&&(side==='ALL'||r.net_role===side));
 return filtered.sort((a,b)=>{const av=a[sort],bv=b[sort];const delta=typeof av==='string'?av.localeCompare(String(bv)):Number(av)-Number(bv);return (descending?-delta:delta)||a.broker_code.localeCompare(b.broker_code);});
}
export function brokerQualityLabel(status:string){
 return status==='BROKER_DATA_MISSING'?'Data broker belum tersedia':status==='VOLUME_SCOPE_MISMATCH'?'Volume broker berbeda dari data harian':status==='BUY_SELL_IMBALANCE'?'Total beli/jual belum cocok':'Volume cocok · kelengkapan sumber belum diverifikasi';
}
export function observationLabel(value:string){return value==='RETURNED'?'Tercatat':value==='BROKER_DATA_MISSING'?'Data sesi belum tersedia':'Broker tidak dikembalikan';}
