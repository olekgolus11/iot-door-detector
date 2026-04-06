import { ControlPanel } from "./ControlPanel";
import { DoorComparisonChart, EntryLeaveBars, OccupancyTrendChart } from "./Charts";

export function DashboardPage({
  summary,
  controlState,
  recentEvents,
  controlStatus,
  health,
  onUpdateControlState,
}) {
  return (
    <div className="dashboard-page">
      <section className="hero hero-dashboard">
        <div className="hero-copy-wrap">
          <p className="eyebrow">Live operator view</p>
          <h2>Clear live monitoring for a room that changes minute by minute.</h2>
          <p className="hero-copy">
            The dashboard keeps the data legible during demos: the room count is obvious, chart
            scales explain themselves, and every live panel is anchored to the same backend
            snapshot.
          </p>
        </div>
        <div className="hero-occupancy">
          <p className="panel-label">Current occupancy</p>
          <div className="occupancy-value">{summary.occupancy ?? 0}</div>
          <p className="hero-mode">
            {controlState.collection_enabled ? "Collecting" : "Paused"} in{" "}
            <strong>{controlState.active_source_mode}</strong> mode
          </p>
        </div>
      </section>

      <section className="metric-strip">
        <article className="metric-card">
          <span>Total entries</span>
          <strong>{summary.total_enters ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Total leaves</span>
          <strong>{summary.total_leaves ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Accepted events</span>
          <strong>{summary.system_status?.accepted_events ?? 0}</strong>
        </article>
        <article className="metric-card">
          <span>Rejected events</span>
          <strong>{summary.system_status?.rejected_events ?? 0}</strong>
        </article>
      </section>

      <section className="dashboard-grid dashboard-grid-large">
        <ControlPanel
          controlState={controlState}
          onUpdateControlState={onUpdateControlState}
          status={controlStatus}
        />
        <article className="panel status-panel">
          <div className="panel-header">
            <h2>System pulse</h2>
            <span>{health.status ?? "local"}</span>
          </div>
          <div className="status-list">
            <div>
              <strong>Source mode</strong>
              <span>{controlState.active_source_mode}</span>
            </div>
            <div>
              <strong>Collection</strong>
              <span>{controlState.collection_enabled ? "enabled" : "paused"}</span>
            </div>
            <div>
              <strong>Baseline</strong>
              <span>{controlState.baseline_occupancy ?? 0}</span>
            </div>
            <div>
              <strong>Rejected flow</strong>
              <span>{summary.system_status?.rejected_events ?? 0} dropped</span>
            </div>
          </div>
        </article>
      </section>

      {!controlState.collection_enabled ? (
        <section className="paused-banner">
          Collection is paused. Incoming events are tracked as rejected debug records and do not
          change the counter or charts.
        </section>
      ) : null}

      <section className="chart-grid">
        <article className="panel">
          <div className="panel-header">
            <h2>Occupancy trend</h2>
            <span>People currently in the room</span>
          </div>
          <OccupancyTrendChart data={summary.occupancy_timeline} />
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Entries vs leaves</h2>
            <span>Movement by recent time bucket</span>
          </div>
          <EntryLeaveBars data={summary.entries_vs_leaves} />
        </article>
      </section>

      <section className="chart-grid">
        <article className="panel">
          <div className="panel-header">
            <h2>Per-door comparison</h2>
            <span>Live accepted totals by door</span>
          </div>
          <DoorComparisonChart data={summary.per_door} />
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Recent accepted events</h2>
            <span>Compact preview</span>
          </div>
          <div className="recent-event-list">
            {recentEvents.length === 0 ? (
              <p className="empty-state">Recent accepted events will appear here once a source is active.</p>
            ) : (
              recentEvents.map((event, index) => (
                <div
                  key={`${event.timestamp}-${event.door_id}-${index}`}
                  className={`recent-event ${event.direction}`}
                >
                  <div>
                    <strong>{event.direction}</strong>
                    <span>{event.door_id}</span>
                  </div>
                  <div>
                    <span>{event.source_type ?? "unknown"}</span>
                    <time>{event.timestamp}</time>
                  </div>
                </div>
              ))
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
