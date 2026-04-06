export function EventTable({ events, filters, onFiltersChange }) {
  return (
    <article className="panel table-panel">
      <div className="panel-header">
        <h2>Retained logs</h2>
        <span>SQLite-backed history</span>
      </div>
      <div className="filter-row">
        <label>
          Door ID
          <input
            value={filters.doorId}
            onChange={(event) =>
              onFiltersChange((current) => ({ ...current, doorId: event.target.value }))
            }
            placeholder="door-a"
          />
        </label>
        <label>
          Since
          <input
            value={filters.since}
            onChange={(event) =>
              onFiltersChange((current) => ({ ...current, since: event.target.value }))
            }
            placeholder="2026-04-06T18:00:00Z"
          />
        </label>
      </div>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Door</th>
              <th>Direction</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 ? (
              <tr>
                <td colSpan="3" className="empty-state">
                  No retained events available yet.
                </td>
              </tr>
            ) : (
              events.map((event, index) => (
                <tr key={`${event.timestamp}-${event.door_id}-${index}`}>
                  <td>{event.timestamp}</td>
                  <td>{event.door_id}</td>
                  <td>{event.direction}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
}
