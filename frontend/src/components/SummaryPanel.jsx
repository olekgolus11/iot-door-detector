export function SummaryPanel({ summary }) {
  return (
    <article className="panel summary-panel">
      <div className="panel-header">
        <h2>Analysis snapshot</h2>
        <span>Simple totals for class demos</span>
      </div>
      <div className="summary-stats">
        <div>
          <strong>{summary.total_enters ?? 0}</strong>
          <span>Total enters</span>
        </div>
        <div>
          <strong>{summary.total_leaves ?? 0}</strong>
          <span>Total leaves</span>
        </div>
      </div>
      <div className="door-breakdown">
        {(summary.per_door ?? []).length === 0 ? (
          <p className="empty-state">Door-level analytics will appear after events arrive.</p>
        ) : (
          summary.per_door.map((door) => (
            <div key={door.door_id} className="door-row">
              <span>{door.door_id}</span>
              <span>{door.enters} in / {door.leaves} out</span>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

