import {useEffect,useState} from "react";
import {getManifest} from "../lib/api";
import {isPilot} from "../lib/pilot";
export function PilotBanner(){
  const [experimental,setExperimental]=useState(false);
  const [count,setCount]=useState(3);
  const [snapshot,setSnapshot]=useState<string|null>(null);
  useEffect(()=>{let alive=true;getManifest().then(m=>{if(alive&&isPilot(m.methodology_version)){setSnapshot(m.as_of);setCount(m.symbols.length);setExperimental(m.methodology_version.includes("valid-baseline"));};}).catch(()=>{});return()=>{alive=false;};},[]);
  return snapshot?<aside className="pilot-banner" role="note"><strong>Cakupan {count} saham{experimental?" · baseline alternatif":""}</strong><span>Snapshot {snapshot} · histori 1 April–30 September 2026 · belum mencakup seluruh pasar.{experimental?" Eksperimen: 20 observasi valid dalam 25 sesi; gap tetap ditandai.":""}</span></aside>:null;
}
