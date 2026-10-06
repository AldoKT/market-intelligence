import type { ActivityPoint, ActivityPayload, InvestigationListItem } from "../types";
export function withLatestPrice(item:InvestigationListItem,data:ActivityPayload):InvestigationListItem {
 const latest=data.series.at(-1),previous=data.series.at(-2);
 if(latest?.date!==data.as_of)return item;
 const close=latest.close,prev=previous?.close;
 return {...item,close:item.close??close,daily_change_pct:item.daily_change_pct??(close!=null&&prev!=null&&prev!==0?(close/prev-1)*100:null)};
}


export function isPilot(version: string) { return version.startsWith("phase1-json-pilot-"); }
export function sessionFinding(p: ActivityPoint) {
  if (p.quality?.evaluation_status === "NOT_EVALUATED" || p.spot_hit == null)
    return "Belum dapat dinilai: data sesi atau baseline sebelumnya belum lengkap.";
  if (p.lifecycle_state == null) return "Status investigasi belum diketahui pada awal segmen; hasil deteksi sesi tetap tersedia.";
  if (p.spot_hit) return "Hard Spot gate satisfied; unusual activity and compression aligned.";
  if (p.lifecycle_state === "NO_INVESTIGATION") return "Tidak ada investigasi aktif pada sesi yang telah dinilai.";
  if (p.lifecycle_state === "CLOSED") return "Investigation closed under the consecutive unsupported-session rule.";
  if (p.lifecycle_state === "WEAKENING") return "Support weakened; monitor the consecutive unsupported-session rule.";
  if (p.lifecycle_state === "ESTABLISHED") return "Persistent evidence remains active across the recent window.";
  if (p.lifecycle_state === "DEVELOPING") return "Evidence continues across multiple sessions.";
  return "Investigation opened and awaits persistence confirmation.";
}
export function qualityReason(reason: string) {
  const labels: Record<string,string> = {
    current_broker_missing_or_scope_mismatch: "Data broker tidak tersedia atau volume belum cocok dengan data harian.",
    current_foreign_flow_missing: "Data foreign flow sesi ini tidak tersedia.",
    prior_20_session_activity_baseline_incomplete: "Baseline 20 sesi sebelumnya belum lengkap."
  };
  return labels[reason] ?? "Data yang dibutuhkan untuk penilaian belum lengkap.";
}
