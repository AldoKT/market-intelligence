import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getActivity, getHistory } from "../lib/api";
import type {
  ActivityPayload,
  HistoryPayload
} from "../types";
import { SimpleLineChart } from "../components/SimpleLineChart";
import { StatusBadge } from "../components/StatusBadge";
import { formatDate, formatNumber } from "../lib/format";

export function HistoryPage() {
  const { symbol = "" } = useParams();
  const [history, setHistory] = useState<HistoryPayload | null>(null);
  const [activity, setActivity] = useState<ActivityPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    Promise.all([getHistory(symbol), getActivity(symbol)])
      .then(([historyPayload, activityPayload]) => {
        if (!alive) return;
        setHistory(historyPayload);
        setActivity(activityPayload);
      })
      .catch((err: Error) => {
        if (alive) setError(err.message);
      });

    return () => {
      alive = false;
    };
  }, [symbol]);

  const pricePoints = useMemo(() => {
    if (!activity) return [];

    return activity.series.map((point) => ({
      x: point.date,
      y: point.close,
      flag: point.spot_hit
    }));
  }, [activity]);

  if (error) {
    return (
      <div className="error-card workspace-page">
        <h2>Unable to load History</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (!history || !activity) {
    return (
      <div className="workspace-page">
        <div className="skeleton skeleton-card" />
      </div>
    );
  }

  return (
    <section className="workspace-page">
      <section className="card history-chart-card">
        <div className="section-heading">
          <div>
            <div className="eyebrow">Price & Investigation Timeline</div>
            <h2>Historical investigation context</h2>
          </div>
        </div>

        <SimpleLineChart
          points={pricePoints}
          height={300}
          emptyLabel="Price history unavailable"
        />

        <div className="chart-legend-row">
          <span>
            <i className="legend-line" /> close price
          </span>
          <span>
            <i className="legend-dot-flag" /> hard Spot hit
          </span>
        </div>
      </section>

      <section className="history-layout">
        <div className="card event-timeline-card">
          <div className="section-heading">
            <div>
              <div className="eyebrow">Event Timeline</div>
              <h3>Lifecycle changes</h3>
            </div>
          </div>

          <div className="event-timeline">
            {history.events
              .slice()
              .reverse()
              .map((event, index) => (
                <div
                  className="timeline-event"
                  key={`${event.date}-${event.event_type}-${index}`}
                >
                  <div
                    className={`timeline-marker ${
                      event.event_type === "SPOT_HIT"
                        ? "timeline-marker-spot"
                        : ""
                    }`}
                  />

                  <div className="timeline-event-content">
                    <div className="timeline-event-head">
                      <strong>{event.event_type.replaceAll("_", " ")}</strong>
                      <span>{formatDate(event.date)}</span>
                    </div>

                    <div className="timeline-event-state">
                      <StatusBadge state={event.state} />
                    </div>

                    <p>{event.note}</p>
                  </div>
                </div>
              ))}
          </div>
        </div>

        <aside className="card episode-history-card">
          <div className="eyebrow">Past Investigations</div>
          <h3>{history.episodes.length} episode(s)</h3>

          <div className="episode-list">
            {history.episodes
              .slice()
              .reverse()
              .map((episode) => (
                <div className="episode-item" key={episode.investigation_id}>
                  <div className="episode-item-head">
                    <div>
                      <strong>{formatDate(episode.opened_at)}</strong>
                      <span>
                        {episode.closed
                          ? `Closed ${formatDate(episode.closed_at)}`
                          : "Still open"}
                      </span>
                    </div>
                    <StatusBadge state={episode.peak_state} />
                  </div>

                  <div className="episode-stats">
                    <EpisodeStat
                      label="Active sessions"
                      value={String(episode.active_sessions)}
                    />
                    <EpisodeStat
                      label="Hard hits"
                      value={String(episode.hard_hits)}
                    />
                    <EpisodeStat
                      label="Support"
                      value={String(episode.support_sessions)}
                    />
                    <EpisodeStat
                      label="Max confidence"
                      value={
                        episode.max_evidence_confidence == null
                          ? "—"
                          : `${formatNumber(
                              episode.max_evidence_confidence,
                              0
                            )}/100`
                      }
                    />
                  </div>

                  {episode.close_reason && (
                    <small>
                      Close reason:{" "}
                      {episode.close_reason.replaceAll("_", " ")}
                    </small>
                  )}
                </div>
              ))}
          </div>
        </aside>
      </section>
    </section>
  );
}

function EpisodeStat({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
