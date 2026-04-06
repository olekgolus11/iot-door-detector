function FilterField({ label, children }) {
  return (
    <label className="filter-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function EventRows({ rows, rejected = false }) {
  if (!rows.length) {
    return (
      <tr>
        <td colSpan={rejected ? 7 : 5} className="empty-state">
          No matching rows yet.
        </td>
      </tr>
    );
  }

  return rows.map((row, index) => (
    <tr key={`${row.timestamp}-${row.door_id}-${index}`}>
      <td>{row.timestamp}</td>
      <td>{row.door_id ?? "-"}</td>
      <td>{row.direction ?? "-"}</td>
      <td>{row.source_type ?? "-"}</td>
      <td>{row.publisher_id ?? "-"}</td>
      {rejected ? (
        <>
          <td>{row.reason_code}</td>
          <td>{row.reason_message}</td>
        </>
      ) : null}
    </tr>
  ));
}

export function DebugPage({
  summary,
  controlState,
  filters,
  events,
  rejectedEvents,
  availableDoors,
  onFiltersChange,
}) {
  return (
    <div className="debug-page">
      <section className="hero hero-debug">
        <div>
          <p className="eyebrow">Debug workspace</p>
          <h2>Raw telemetry and control-state inspection in one quieter workspace.</h2>
          <p className="hero-copy">
            Use this page when you need detail rather than presentation: door-level payloads,
            rejected events, and exact filtered slices without overloading the main dashboard.
          </p>
        </div>
        <div className="debug-state-card">
          <p className="panel-label">Current control state</p>
          <strong>{controlState.collection_enabled ? "Collecting" : "Paused"}</strong>
          <span>{controlState.active_source_mode} source</span>
          <span>Baseline {controlState.baseline_occupancy ?? 0}</span>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Debug filters</h2>
          <span>Apply to accepted and rejected tables</span>
        </div>
        <div className="filter-grid">
          <FilterField label="Door">
            <select
              value={filters.doorId}
              onChange={(event) =>
                onFiltersChange((current) => ({ ...current, doorId: event.target.value }))
              }
            >
              <option value="">All doors</option>
              {availableDoors.map((doorId) => (
                <option key={doorId} value={doorId}>
                  {doorId}
                </option>
              ))}
            </select>
          </FilterField>

          <FilterField label="Direction">
            <select
              value={filters.direction}
              onChange={(event) =>
                onFiltersChange((current) => ({ ...current, direction: event.target.value }))
              }
            >
              <option value="">Both</option>
              <option value="enter">Enter</option>
              <option value="leave">Leave</option>
            </select>
          </FilterField>

          <FilterField label="Source">
            <select
              value={filters.sourceType}
              onChange={(event) =>
                onFiltersChange((current) => ({ ...current, sourceType: event.target.value }))
              }
            >
              <option value="">All sources</option>
              <option value="mock">Mock</option>
              <option value="camera">Camera</option>
              <option value="unknown">Unknown</option>
            </select>
          </FilterField>

          <FilterField label="Since">
            <input
              value={filters.since}
              onChange={(event) =>
                onFiltersChange((current) => ({ ...current, since: event.target.value }))
              }
              placeholder="2026-04-06T18:00:00Z"
            />
          </FilterField>

          <FilterField label="Until">
            <input
              value={filters.until}
              onChange={(event) =>
                onFiltersChange((current) => ({ ...current, until: event.target.value }))
              }
              placeholder="2026-04-06T19:00:00Z"
            />
          </FilterField>
        </div>
      </section>

      <section className="debug-grid">
        <article className="panel table-panel">
          <div className="panel-header">
            <h2>Accepted events</h2>
            <span>{summary.system_status?.accepted_events ?? 0} total</span>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Door</th>
                  <th>Direction</th>
                  <th>Source</th>
                  <th>Publisher</th>
                </tr>
              </thead>
              <tbody>
                <EventRows rows={events} />
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel table-panel">
          <div className="panel-header">
            <h2>Rejected events</h2>
            <span>{summary.system_status?.rejected_events ?? 0} total</span>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Door</th>
                  <th>Direction</th>
                  <th>Source</th>
                  <th>Publisher</th>
                  <th>Reason code</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                <EventRows rows={rejectedEvents} rejected />
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </div>
  );
}
