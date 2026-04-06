export function EventFeed({ events }) {
  return (
    <article className="panel">
      <div className="panel-header">
        <h2>Live event feed</h2>
        <span>{events.length} recent</span>
      </div>
      <div className="event-feed">
        {events.length === 0 ? (
          <p className="empty-state">No events yet. Start the mock publisher or YOLO publisher.</p>
        ) : (
          events.map((event, index) => (
            <div key={`${event.timestamp}-${index}`} className={`event-card ${event.direction}`}>
              <span className="event-direction">{event.direction}</span>
              <span>{event.door_id}</span>
              <time>{event.timestamp}</time>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

