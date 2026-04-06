function shortLabel(value) {
  return value?.slice(11, 16) ?? "--:--";
}

export function OccupancyTrendChart({ data }) {
  if (!data?.length) {
    return <p className="empty-state">Occupancy trend appears after accepted events arrive.</p>;
  }

  const width = 560;
  const height = 220;
  const maxValue = Math.max(...data.map((point) => point.occupancy), 1);
  const points = data
    .map((point, index) => {
      const x = (index / Math.max(data.length - 1, 1)) * (width - 40) + 20;
      const y = height - 28 - (point.occupancy / maxValue) * (height - 56);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="chart-shell">
      <svg viewBox={`0 0 ${width} ${height}`} className="line-chart" role="img">
        <defs>
          <linearGradient id="occupancy-fill" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(21, 122, 104, 0.35)" />
            <stop offset="100%" stopColor="rgba(21, 122, 104, 0.03)" />
          </linearGradient>
        </defs>
        <polyline points={points} fill="none" stroke="#157a68" strokeWidth="4" />
        {data.map((point, index) => {
          const x = (index / Math.max(data.length - 1, 1)) * (width - 40) + 20;
          const y = height - 28 - (point.occupancy / maxValue) * (height - 56);
          return <circle key={point.bucket} cx={x} cy={y} r="4" fill="#157a68" />;
        })}
      </svg>
      <div className="chart-label-row">
        {data.map((point) => (
          <span key={point.bucket}>{shortLabel(point.bucket)}</span>
        ))}
      </div>
    </div>
  );
}

export function EntryLeaveBars({ data }) {
  if (!data?.length) {
    return <p className="empty-state">Entries and leaves will chart themselves once events start flowing.</p>;
  }

  const maxValue = Math.max(
    ...data.flatMap((item) => [item.enters ?? 0, item.leaves ?? 0]),
    1
  );

  return (
    <div className="bar-list">
      {data.map((item) => (
        <div className="bar-row" key={item.bucket}>
          <span>{shortLabel(item.bucket)}</span>
          <div className="bar-pair">
            <div className="bar enter" style={{ width: `${((item.enters ?? 0) / maxValue) * 100}%` }}>
              {item.enters ?? 0}
            </div>
            <div className="bar leave" style={{ width: `${((item.leaves ?? 0) / maxValue) * 100}%` }}>
              {item.leaves ?? 0}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function DoorComparisonChart({ data }) {
  if (!data?.length) {
    return <p className="empty-state">Per-door comparisons appear when at least one door reports accepted events.</p>;
  }

  const maxValue = Math.max(
    ...data.flatMap((door) => [door.enters ?? 0, door.leaves ?? 0]),
    1
  );

  return (
    <div className="door-chart">
      {data.map((door) => (
        <div className="door-chart-row" key={door.door_id}>
          <div className="door-chart-meta">
            <strong>{door.door_id}</strong>
            <span>{door.net >= 0 ? `+${door.net}` : door.net} net</span>
          </div>
          <div className="door-bars">
            <div className="door-bar enter" style={{ width: `${((door.enters ?? 0) / maxValue) * 100}%` }} />
            <div className="door-bar leave" style={{ width: `${((door.leaves ?? 0) / maxValue) * 100}%` }} />
          </div>
          <p>{door.enters} in / {door.leaves} out</p>
        </div>
      ))}
    </div>
  );
}
