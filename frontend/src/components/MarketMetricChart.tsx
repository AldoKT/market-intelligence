import { useEffect, useRef, useState } from "react";
import { AreaSeries, HistogramSeries, ColorType, CrosshairMode, createChart, createSeriesMarkers } from "lightweight-charts";
import type { IChartApi, Time } from "lightweight-charts";
import { activityValue } from "../lib/marketActivityView";

type Point={date:string;value:number|null;hardSpot:boolean};
export function MarketMetricChart({points,unit,title,height=270,onSession,signed=false}:{points:Point[];unit:"idr"|"shares"|"count"|"ratio";title:string;height?:number;onSession?:(date:string|null)=>void;signed?:boolean}){
 const host=useRef<HTMLDivElement>(null);const api=useRef<IChartApi|null>(null);const hover=useRef(onSession);hover.current=onSession;
 const [mode,setMode]=useState<"area"|"bars">("bars");const [legend,setLegend]=useState("");
 useEffect(()=>{
  if(!host.current)return;
  const last=points.at(-1);const initial=`${title} · ${activityValue(last?.value,unit)}`;setLegend(initial);
  const chart=createChart(host.current,{autoSize:true,height,layout:{background:{type:ColorType.Solid,color:"transparent"},textColor:"#b8c5d6",attributionLogo:true},grid:{vertLines:{visible:false},horzLines:{color:"#33404f"}},crosshair:{mode:CrosshairMode.Normal,horzLine:{color:"#93c5fd",labelBackgroundColor:"#2c3d52"},vertLine:{color:"#8799b0",labelBackgroundColor:"#2c3d52"}},rightPriceScale:{borderVisible:false},timeScale:{borderVisible:false,rightOffset:5},handleScroll:{pressedMouseMove:true,mouseWheel:true,horzTouchDrag:true,vertTouchDrag:false},handleScale:{mouseWheel:true,pinch:true,axisPressedMouseMove:true}});
  api.current=chart;
  const priceFormat={type:"custom" as const,formatter:(v:number)=>activityValue(v,unit),minMove:unit==="ratio"?.01:1};
  const series=mode==="area"?chart.addSeries(AreaSeries,{lineColor:"#67e8f9",topColor:"rgba(103,232,249,.18)",bottomColor:"rgba(103,232,249,0)",lineWidth:2,priceFormat,lastValueVisible:false,priceLineVisible:false}):chart.addSeries(HistogramSeries,{color:"#93c5fd",priceFormat,lastValueVisible:false,priceLineVisible:false});
  series.setData(points.map(p=>p.value===null?{time:p.date as Time}:{time:p.date as Time,value:p.value,...(mode==="bars"?{color:signed&&p.value<0?"#ff8e9c":p.hardSpot?"#67e8f9":"#93c5fd"}:{})}));
  createSeriesMarkers(series,points.filter(p=>p.hardSpot&&p.value!==null).map(p=>({time:p.date as Time,position:"atPriceMiddle" as const,price:p.value!,color:"#f3f6fa",shape:"square" as const,size:1})));
  if(signed)series.createPriceLine({price:0,color:"#8799b0",lineWidth:1,lineStyle:2,axisLabelVisible:false});
  if(unit==="ratio")series.createPriceLine({price:1,color:"#93c5fd",lineStyle:2,lineWidth:1,axisLabelVisible:true,axisLabelColor:"#2c3d52",axisLabelTextColor:"#f3f6fa",title:"1×"});
  chart.subscribeCrosshairMove(e=>{const p=e.seriesData.get(series);if(!e.time||!p||!("value" in p)){setLegend(initial);hover.current?.(null);return;}setLegend(`${String(e.time)} · ${activityValue(p.value,unit)}`);hover.current?.(String(e.time));});
  chart.timeScale().fitContent();return()=>{api.current=null;chart.remove();};
 },[points,unit,title,height,mode,signed]);
 function zoom(f:number){const scale=api.current?.timeScale();const range=scale?.getVisibleLogicalRange();if(scale&&range){const mid=(range.from+range.to)/2;const half=(range.to-range.from)*f/2;scale.setVisibleLogicalRange({from:mid-half,to:mid+half});}}
 return <section className="ma-metric-chart" aria-label={`Grafik aktivitas interaktif ${title}`}><div className="ov-chart-bar"><strong>{title}<span className="ma-unit"> {unit==="idr"?"/ IDR":unit==="shares"?"/ Shares":unit==="ratio"?"/ Relative":"/ Trades"}</span></strong><div className="ov-chart-controls"><button aria-pressed={mode==="bars"} onClick={()=>setMode("bars")}>Bars</button><button aria-pressed={mode==="area"} onClick={()=>setMode("area")}>Area</button><button aria-label="Perbesar aktivitas" onClick={()=>zoom(.65)}>+</button><button aria-label="Perkecil aktivitas" onClick={()=>zoom(1.5)}>−</button><button onClick={()=>api.current?.timeScale().fitContent()}>Reset</button></div></div><div className="ov-chart-legend" role="status">{legend}</div><div ref={host} className="ma-metric-canvas" style={{height}}/><div className="ov-chart-foot"><span>{signed?"Biru: net buy · Coral: net sell":"□ Hard spot · Geser / scroll untuk jelajahi"}</span><a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">Charts by TradingView</a></div></section>;
}
