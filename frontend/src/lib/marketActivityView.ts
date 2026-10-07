import type { ActivityPoint } from "../types";
export type ActivityMetric = "turnover" | "volume" | "transactions" | "avgTrade";
export const activityMetrics:Record<ActivityMetric,{label:string;unit:"idr"|"shares"|"count";actual:keyof ActivityPoint;relative:keyof ActivityPoint}>={
 turnover:{label:"Turnover",unit:"idr",actual:"turnover_idr",relative:"relative_turnover"},
 volume:{label:"Volume",unit:"shares",actual:"volume",relative:"relative_volume"},
 transactions:{label:"Transactions",unit:"count",actual:"transaction_count",relative:"relative_transaction_count"},
 avgTrade:{label:"Average trade",unit:"idr",actual:"avg_trade_value_idr",relative:"relative_avg_trade_value"}
};
const finite=(v:unknown)=>typeof v==="number"&&Number.isFinite(v)?v:null;
export function activityWindow(points:ActivityPoint[],size:number){
 const sorted=[...new Map(points.map(p=>[p.date,p])).values()].sort((a,b)=>a.date.localeCompare(b.date));
 return size>0 ? sorted.slice(-size) : sorted;
}
export function marketActivityView(rows:ActivityPoint[],metric:ActivityMetric){
 const def=activityMetrics[metric];const relative=!rows.some(p=>finite(p[def.actual])!==null)&&rows.some(p=>finite(p[def.relative])!==null);
 const key=relative?def.relative:def.actual;const points=rows.map(p=>({date:p.date,value:finite(p[key]),hardSpot:p.spot_hit===true}));
 const current=points.at(-1)?.value??null;
 const usable=points.filter((p):p is typeof p & {value:number}=>p.value!==null);
 const peak=usable.reduce<(typeof usable)[number]|null>((best,p)=>!best||p.value>best.value?p:best,null);
 return {title:relative?`Relative ${def.label}`:def.label,unit:relative?"ratio" as const:def.unit,points,current,peak,hardSpots:points.filter(p=>p.hardSpot&&p.value!==null).length};
}
export function activityValue(v:number|null|undefined,unit:"idr"|"shares"|"count"|"ratio"){
 if(v==null||!Number.isFinite(v))return "—";
 if(unit==="ratio")return `${v.toLocaleString("id-ID",{maximumFractionDigits:2})}×`;
 const abs=Math.abs(v);const scale=abs>=1e12?1e12:abs>=1e9?1e9:abs>=1e6?1e6:1;
 const suffix=scale===1e12?"T":scale===1e9?"B":scale===1e6?"M":"";
 const text=(v/scale).toLocaleString("id-ID",{maximumFractionDigits:scale===1?0:2})+suffix;
 return unit==="idr"?`Rp ${text}`:text;
}
