import type { ActivityPayload } from "../types";
export function PilotQualityNotice({data}:{data:ActivityPayload}) {
  if(!data.quality) return null;
  return <aside className="pilot-quality-notice" role="note"><strong>Kualitas data pilot</strong><p>{data.quality.evaluated_sessions} dari {data.quality.analysis_sessions} sesi dapat dinilai; {data.quality.withheld_sessions} sesi <b>belum dapat dinilai</b>. Status investigasi pada awal segmen juga dapat belum diketahui. Data kosong tidak dianggap sebagai nol atau tidak ada sinyal.</p><details><summary>Rincian data</summary><p>Broker / foreign flow tidak tersedia: {data.quality.missing_dates.join(", ")}. Volume broker belum cocok: {data.quality.broker_scope_mismatch_dates.join(", ")}. Gap juga memengaruhi baseline sesi berikutnya.</p></details></aside>;
}
