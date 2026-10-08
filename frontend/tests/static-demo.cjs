const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const ts = require('typescript');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root,'src/lib/staticApi.ts'),'utf8').replaceAll('import.meta.env.BASE_URL',JSON.stringify('/market-intelligence/'));
const code = ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
let requests = 0;
const exportsObject = {};
vm.runInNewContext(code,{exports:exportsObject,URL,URLSearchParams,Map,Object,Promise,Error,encodeURIComponent,decodeURIComponent,fetch:async url=>{
 assert.ok(url.startsWith('/market-intelligence/data/'));
 requests++;
 const file = path.join(root,'dist',url.slice('/market-intelligence/'.length));
 const exists = fs.existsSync(file);
 return {ok:exists,status:exists?200:404,json:async()=>JSON.parse(fs.readFileSync(file,'utf8'))};
}});
(async()=>{
 const read = exportsObject.getStaticJson;
 const all = await read('/api/investigations');
 assert.equal(all.items.length,28);
 const filtered = await read('/api/investigations?q=bbca');
 assert.deepEqual(Array.from(filtered.items,x=>x.symbol),['BBCA']);
 for(const item of all.items){
  const symbol=item.symbol;
  for(const page of ['summary','activity','context','history']) assert.ok(await read(`/api/investigations/${symbol}/${page}`));
  const index=await read(`/api/brokers/${symbol}`);
  assert.equal(index.default_date,'2026-09-30');
  const history=JSON.parse(fs.readFileSync(path.join(root,`dist/data/brokers/history/${symbol}.json`),'utf8'));
  for(const through of [index.dates[0],index.dates[Math.floor(index.dates.length/2)],index.default_date]){
   const dates=index.dates.filter(d=>d<=through);
   const codes=new Set(dates.flatMap(d=>Object.keys(history[d].rows)));
   for(const broker of codes){
    const result=await read(`/api/brokers/${symbol}/history/${broker}?through=${through}`);
    const window=dates.slice(-20);
    assert.equal(result.series.length,window.length);
    for(let i=0;i<window.length;i++){
     const day=history[window[i]];const row=day.rows[broker];const point=result.series[i];
     assert.equal(point.observation,row?'RETURNED':Object.keys(day.rows).length?'NOT_RETURNED':'BROKER_DATA_MISSING');
     assert.equal(point.nval,row?.nval??null);
     assert.equal(point.session_quality,day.quality);
    }
   }
  }
  for(const episode of index.episodes) assert.equal((await read(`/api/brokers/${symbol}/episodes/${episode.investigation_id}`)).symbol,symbol);
 }
 await assert.rejects(read('/api/brokers/BBCA/history/INVALID?through=2026-09-30'));
 await assert.rejects(read('/api/brokers/BBCA/history/XL?through=2099-01-01'));
 const before=requests;await read('/api/investigations');assert.equal(requests,before);
 console.log('PASS static demo: 28 stocks, filters, episodes, history windows, missing values, cutoff guards and cache.');
})().catch(error=>{console.error(error);process.exitCode=1;});
