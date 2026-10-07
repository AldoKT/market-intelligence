import type {BrokerHistoryPoint} from './brokerTypes';
export function brokerChartModel(series:BrokerHistoryPoint[]){
 const points=series.map(row=>({...row,value:row.observation==='RETURNED'&&row.nval!=null&&Number.isFinite(row.nval)?row.nval:null}));
 const values=points.flatMap(p=>p.value==null?[]:[p.value]);
 const rawMin=Math.min(0,...values),rawMax=Math.max(0,...values);
 const span=rawMax-rawMin||1,padding=span*.12;
 const min=rawMin-padding,max=rawMax+padding;
 const scale=Math.max(Math.abs(rawMin),Math.abs(rawMax));
 const divisor=scale>=1e9?1e9:scale>=1e6?1e6:1;
 return {points,min,max,divisor,unit:divisor===1e9?'IDR miliar':divisor===1e6?'IDR juta':'IDR',
  ticks:[max,0,min].filter((v,i,a)=>a.indexOf(v)===i).sort((a,b)=>b-a)};
}
