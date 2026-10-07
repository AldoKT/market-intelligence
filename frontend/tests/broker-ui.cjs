const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const deps=createRequire(path.join(root,'package.json')),ts=deps('typescript');
const loaded=new Map();
function load(file){
 if(loaded.has(file))return loaded.get(file);
 const output={};loaded.set(file,output);
 const input=fs.readFileSync(file,'utf8').replaceAll('import.meta.env','({VITE_API_BASE_URL:"http://127.0.0.1:8001"})');
 const js=ts.transpileModule(input,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 const localRequire=name=>{if(!name.startsWith('.'))return deps(name);const base=path.resolve(path.dirname(file),name);const found=['.ts','.tsx'].map(ext=>base+ext).find(fs.existsSync);return found?load(found):deps(name);};
 vm.runInNewContext(js,{exports:output,require:localRequire,console,URLSearchParams},{filename:file});return output;
}

const {filterBrokers,brokerQualityLabel,observationLabel}=load(root+'/src/lib/brokers.ts');
const rows=[{broker_code:'AA',broker_name:'Alpha',nval:0,net_role:'NET_FLAT',bval:100,sval:100,gross_value_idr:200},{broker_code:'BB',broker_name:null,nval:-20,net_role:'NET_SELL',bval:0,sval:20,gross_value_idr:20},...Array.from({length:6},(_,i)=>({broker_code:'C'+i,broker_name:'Buyer',net_role:'NET_BUY',nval:10+i,bval:10+i,sval:0,gross_value_idr:10+i}))];
assert.equal(filterBrokers(rows,'','ALL','gross_value_idr',true).length,8);
assert.equal(filterBrokers(rows,'','ALL','nval',false)[0].broker_code,'BB');
assert.equal(filterBrokers(rows,'alpha','ALL','nval',true)[0].broker_code,'AA');
assert.equal(filterBrokers(rows,'','NET_FLAT','nval',true)[0].nval,0);
assert.equal(filterBrokers(rows,'','ALL','broker_code',false)[0].broker_code,'AA');
assert.equal(rows[0].broker_code,'AA');
assert.match(brokerQualityLabel('BROKER_DATA_MISSING'),/belum tersedia/);
assert.match(brokerQualityLabel('VOLUME_SCOPE_MISMATCH'),/berbeda/);
assert.match(observationLabel('NOT_RETURNED'),/tidak dikembalikan/);
assert.equal(filterBrokers(rows,'unknown','ALL','nval',true).length,0);
console.log('PASS: all rows including zero-net retained; name/code search, numeric/code sorting, net-side filters, immutable input, missing-source labels (10 assertions).');

const {brokerChartModel}=load(root+'/src/lib/brokerChart.ts');
const sample=[{date:'2026-10-01',observation:'RETURNED',nval:0},{date:'2026-10-02',observation:'NOT_RETURNED',nval:0},{date:'2026-10-05',observation:'RETURNED',nval:1000000000},{date:'2026-10-06',observation:'RETURNED',nval:-500000000}];
const chart=brokerChartModel(sample);
assert.equal(chart.points.length,4);assert.equal(chart.points[0].value,0);assert.equal(chart.points[1].value,null);
assert.equal(chart.points[2].date,'2026-10-05');assert.ok(chart.min<-500000000&&chart.max>1000000000);assert.equal(chart.divisor,1000000000);
const empty=brokerChartModel([]);assert.ok(Number.isFinite(empty.min)&&empty.max>empty.min);
const zero=brokerChartModel([sample[0]]);assert.ok(zero.max>zero.min);
const {renderToStaticMarkup}=deps('react-dom/server'),React=deps('react');
const {BrokerNetChart}=load(root+'/src/components/BrokerNetChart.tsx');
const markup=renderToStaticMarkup(React.createElement(BrokerNetChart,{history:{broker_code:'AA',series:sample}}));
assert.match(markup,/Belum tersedia/);assert.match(markup,/bukan kumulatif/);assert.doesNotMatch(markup,/NaN|Infinity/);
console.log('PASS: chart preserves date slots and null vs zero, signed domain/unit scaling, all-missing/zero domain, accessible rendered legend (11 assertions).');
