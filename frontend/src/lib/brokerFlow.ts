import type {BrokerHistoryPoint} from './brokerTypes';
export function brokerFlowPoints(rows:BrokerHistoryPoint[],metric:'value'|'lot',cumulative:boolean){
 let running=0;return rows.map(p=>{const raw=metric==='value'?p.nval:p.nlot;const valid=p.observation==='RETURNED'&&raw!=null&&Number.isFinite(raw)&&(!cumulative||p.session_quality==='RECONCILED_RESEARCH_CANDIDATE');if(!valid){running=0;return {date:p.date,value:null};}running=cumulative?running+raw!:raw!;return {date:p.date,value:running};});
}
export function brokerFlowSegments(points:{date:string;value:number|null}[]){const segments:{date:string;value:number}[][]=[];let current:{date:string;value:number}[]=[];for(const p of points){if(p.value===null){if(current.length)segments.push(current);current=[];}else current.push({date:p.date,value:p.value});}if(current.length)segments.push(current);return segments;}
