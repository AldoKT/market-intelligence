import type {BrokerHistory} from '../lib/brokerTypes';
import {brokerChartModel} from '../lib/brokerChart';
import {formatDate,formatNumber} from '../lib/format';

export function BrokerNetChart({history}:{history:BrokerHistory}){
 const model=brokerChartModel(history.series),left=78,top=22,width=788,height=175;
 const y=(value:number)=>top+(model.max-value)/(model.max-model.min)*height;
 const zero=y(0),step=width/Math.max(1,model.points.length),barWidth=Math.min(56,step*.65);
 return <figure className="broker-net-chart">
  <figcaption><strong>Net buy / sell per sesi · {history.broker_code}</strong><span>{model.unit}</span></figcaption>
  {!model.points.length?<p>Riwayat belum tersedia.</p>:<svg viewBox="0 0 900 240" role="img" aria-label={`Grafik net buy dan net sell broker ${history.broker_code}, ${model.points.length} sesi`}>
   {model.ticks.map(value=><g key={value}><line x1={left} x2={left+width} y1={y(value)} y2={y(value)} stroke={value===0?'#91a2b9':'#e6ebf2'} strokeDasharray={value===0?undefined:'4 4'}/><text x={left-10} y={y(value)+4} textAnchor="end" fill="#738198" fontSize="11">{formatNumber(value/model.divisor,2)}</text></g>)}
   {model.points.map((point,index)=>{
    const x=left+step*(index+.5),unknown=point.value==null,bad=point.session_quality!=='RECONCILED_RESEARCH_CANDIDATE';
    const value=point.value??0,barTop=Math.min(zero,y(value)),barHeight=Math.abs(y(value)-zero);
    const caption=`${formatDate(point.date)}: ${unknown?'Belum tersedia':`net IDR ${formatNumber(value,0)}${bad?' · data perlu ditinjau':''}`}`;
    return <g key={point.date}>
     {unknown?<g><title>{caption}</title><rect x={x-barWidth/2} y={top} width={barWidth} height={height} fill="#edf0f5"/><text x={x} y={top+height/2} textAnchor="middle" fontSize="14" fill="#8793a4">?</text></g>:value===0?<circle cx={x} cy={zero} r={3} fill={bad?'#c28a27':'#64748b'}><title>{caption}</title></circle>:<rect x={x-barWidth/2} y={barTop} width={barWidth} height={barHeight} rx="2" fill={bad?'#c28a27':value>0?'#16806e':'#b65353'}><title>{caption}</title></rect>}
     {(index===0||index===model.points.length-1||(model.points.length>10&&index%Math.ceil(model.points.length/5)===0))&&<text x={x} y="223" textAnchor="middle" fontSize="11" fill="#738198">{point.date.slice(8,10)}/{point.date.slice(5,7)}</text>}
    </g>;
   })}
  </svg>}
  <div className="broker-chart-legend"><span><i className="buy"/>Net buy</span><span><i className="sell"/>Net sell</span><span><i className="flat"/>Net nol</span><span><i className="unknown"/>Belum tersedia (?)</span><span><i className="warning"/>Data perlu ditinjau</span></div>
  <p>Nilai tiap sesi, bukan kumulatif. Sesi kosong tidak dianggap nol. Arahkan kursor ke batang untuk nilai lengkap; angka rinci tetap tersedia di tabel.</p>
 </figure>;
}
