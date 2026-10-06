import {useEffect,useState} from "react";
import {getManifest} from "../lib/api";
import {isPilot} from "../lib/pilot";
export function PilotBanner(){
  const [snapshot,setSnapshot]=useState<string|null>(null);
  useEffect(()=>{let alive=true;getManifest().then(m=>{if(alive&&isPilot(m.methodology_version))setSnapshot(m.as_of);}).catch(()=>{});return()=>{alive=false;};},[]);
  return snapshot?<aside className="pilot-banner" role="note"><strong>Pilot ANTM · INCO · BBCA</strong><span>Snapshot {snapshot} · histori 1 April–30 September 2026 · belum mencakup seluruh pasar.</span></aside>:null;
}
