const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const deps=createRequire(root+'/package.json'),ts=deps('typescript');
const output={};const source=fs.readFileSync(root+'/src/lib/episodeChart.ts','utf8');
vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports:output});
const {episodeChartWindow}=output;
const payloadRoot=path.resolve(root,'../payloads/valid_baseline_v1/tickers');
let episodes=0,spots=0;
for(const symbol of fs.readdirSync(payloadRoot)){
 const activity=JSON.parse(fs.readFileSync(path.join(payloadRoot,symbol,'activity.json'),'utf8'));
 const history=JSON.parse(fs.readFileSync(path.join(payloadRoot,symbol,'history.json'),'utf8'));
 for(const episode of history.episodes){
  const w=episodeChartWindow(activity.series,episode);
  assert.equal(w.hardSpots.length,episode.hard_hits,`${episode.investigation_id}: hard spot count`);
  for(const p of w.hardSpots){assert.equal(p.spot_hit,true);assert.ok(p.date>=episode.opened_at&&p.date<=episode.last_linked_at);assert.ok(p.high>=p.low);}
  assert.ok(w.points.every(p=>p.date<=activity.as_of));
  episodes++;spots+=w.hardSpots.length;
 }
}
const episode={opened_at:'2026-09-10',last_linked_at:'2026-09-11',closed_at:'2026-09-12'};
const point=(date,spot_hit,low=10,high=20)=>({date,spot_hit,low,high,close:15});
const edge=episodeChartWindow([point('2026-09-09',true),point('2026-09-10',null),point('2026-09-11',true),point('2026-09-12',true)],episode);
assert.deepEqual(Array.from(edge.hardSpots,p=>p.date),['2026-09-11']);
assert.equal(episodeChartWindow([point('2026-09-11',true,null,20)],episode).hardSpots.length,0);
assert.equal(episodeChartWindow([point('2026-09-01',true)],episode).points.length,0);
function lum(hex){return hex.match(/\w\w/g).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);}
function contrast(a,b){const x=lum(a.slice(1)),y=lum(b.slice(1));return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
const colors=[];
for(const bg of ['#111418','#20262e','#29313b','#222832','#2c3d52'])for(const fg of ['#f3f6fa','#b8c5d6','#93c5fd','#67e8f9']){const ratio=contrast(fg,bg);assert.ok(ratio>=4.5,`${fg}/${bg} ${ratio}`);colors.push({fg,bg,ratio:Number(ratio.toFixed(2))});}
assert.ok(contrast('#111418','#93c5fd')>=4.5);
assert.ok(contrast('#bfdbfe','#24394f')>=4.5);
assert.ok(contrast('#8799b0','#222832')>=3);
console.log(JSON.stringify({episodes,hardSpots:spots,paletteTextMinimum:Math.min(...colors.map(c=>c.ratio)),chartLineContrast:contrast('#67e8f9','#20262e').toFixed(2),hardSpotContrast:contrast('#93c5fd','#20262e').toFixed(2),checks:'PASS'},null,2));
