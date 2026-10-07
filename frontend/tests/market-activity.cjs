const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const ts=require('typescript'),root=path.resolve(__dirname,'..'),out={};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(root+'/src/lib/marketActivityView.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports:out});
const {activityWindow,marketActivityView,activityValue,activityMetrics}=out;
const rows=[{date:'2026-09-29',turnover_idr:100,relative_turnover:2,spot_hit:true},{date:'2026-09-30',turnover_idr:null,relative_turnover:3,spot_hit:null}];
assert.equal(marketActivityView(rows,'turnover').current,null);
assert.equal(marketActivityView(rows,'turnover').points[1].value,null);
assert.equal(marketActivityView(rows,'turnover').unit,'idr');
const rel=marketActivityView(rows.map(p=>({...p,turnover_idr:null})),'turnover');assert.equal(rel.unit,'ratio');assert.equal(rel.current,3);
assert.equal(marketActivityView([{...rows[0],turnover_idr:0}],'turnover').current,0);
assert.equal(marketActivityView([{...rows[0],turnover_idr:NaN}],'turnover').unit,'ratio');
assert.equal(marketActivityView([{date:'x',turnover_idr:null,spot_hit:true}],'turnover').hardSpots,0);
assert.equal(activityValue(null,'idr'),'—');assert.equal(activityValue(Infinity,'count'),'—');
assert.equal(activityWindow([rows[1],rows[0],{...rows[0],turnover_idr:7}],1)[0].date,'2026-09-30');
assert.equal(activityWindow([rows[1],rows[0],{...rows[0],turnover_idr:7}],0)[0].turnover_idr,7);
let stocks=0,views=0;const base=path.resolve(root,'../payloads/valid_baseline_v1/tickers');
for(const symbol of fs.readdirSync(base)){const data=JSON.parse(fs.readFileSync(path.join(base,symbol,'activity.json')));stocks++;
for(const n of [20,60,0])for(const metric of Object.keys(activityMetrics)){const w=activityWindow(data.series,n),v=marketActivityView(w,metric);assert.equal(w.length,n||121);assert.equal(v.points.length,w.length);assert.ok(v.points.every(p=>p.value===null||Number.isFinite(p.value)));const key=v.unit==='ratio'?activityMetrics[metric].relative:activityMetrics[metric].actual;for(let i=0;i<w.length;i++)assert.equal(v.points[i].value,typeof w[i][key]==='number'&&Number.isFinite(w[i][key])?w[i][key]:null);views++;}}
console.log(JSON.stringify({stocks,views,missingValues:'preserved',unitFallback:'PASS',checks:'PASS'}));
