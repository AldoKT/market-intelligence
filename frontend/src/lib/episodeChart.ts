import type { ActivityPoint, EpisodeSummary } from "../types";

export function episodeChartWindow(points: ActivityPoint[], episode: EpisodeSummary) {
  const ordered = [...new Map(points.map(p => [p.date, p])).values()].sort((a,b)=>a.date.localeCompare(b.date));
  const start = ordered.findIndex(p=>p.date >= episode.opened_at);
  if(start < 0) return { points: [] as ActivityPoint[], hardSpots: [] as ActivityPoint[] };
  const endDate = episode.closed_at ?? episode.last_linked_at;
  const end = ordered.findIndex(p=>p.date > endDate);
  const window = ordered.slice(Math.max(0,start-12), Math.min(ordered.length,(end < 0 ? ordered.length : end)+6));
  const hardSpots = window.filter(p=>p.date >= episode.opened_at && p.date <= episode.last_linked_at && p.spot_hit === true && p.low != null && p.high != null && Number.isFinite(p.low) && Number.isFinite(p.high) && p.high >= p.low);
  return { points: window, hardSpots };
}
