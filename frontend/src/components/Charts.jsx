function shortLabel(value) {
  return value?.slice(11, 16) ?? "--:--";
}

export function OccupancyTrendChart({ data }) {
  if (!data?.length) {
    return <p className="empty-state">Occupancy trend appears after accepted events arrive.</p>;
  }

  const width = 620;
  const height = 260;
  const maxValue = Math.max(...data.map((point) => point.occupancy), 1);
  const left = 72;
  const right = 20;
  const top = 24;
  const bottom = 42;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const tickCount = Math.min(5, maxValue + 1);
  const ticks = Array.from({ length: tickCount }, (_, index) => {
    const value = Math.round((maxValue * index) / Math.max(tickCount - 1, 1));
    return tickCount === 1 ? maxValue : value;
  }).filter((value, index, values) => index === 0 || value !== values[index - 1]);
  const points = data
    .map((point, index) => {
      const x = left + (index / Math.max(data.length - 1, 1)) * plotWidth;
      const y = top + plotHeight - (point.occupancy / maxValue) * plotHeight;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="chart-shell">
      <p className="chart-description">People currently counted in the room over time.</p>
      <svg viewBox={`0 0 ${width} ${height}`} className="line-chart" role="img">
        <defs>
          <linearGradient id="occupancy-fill" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(66, 111, 103, 0.14)" />
            <stop offset="100%" stopColor="rgba(66, 111, 103, 0.02)" />
          </linearGradient>
        </defs>
        {ticks.map((tick) => {
          const y = top + plotHeight - (tick / maxValue) * plotHeight;
          return (
            <g key={tick}>
              <line x1={left} y1={y} x2={width - right} y2={y} className="axis-grid" />
              <text x={left - 12} y={y + 4} textAnchor="end" className="axis-tick">
                {tick}
              </text>
            </g>
          );
        })}
        <line x1={left} y1={top} x2={left} y2={top + plotHeight} className="axis-line" />
        <line
          x1={left}
          y1={top + plotHeight}
          x2={width - right}
          y2={top + plotHeight}
          className="axis-line"
        />
        <text
          x="18"
          y={top + plotHeight / 2}
          transform={`rotate(-90 18 ${top + plotHeight / 2})`}
          className="axis-label"
        >
          People in room
        </text>
        <polyline points={points} fill="none" stroke="#426f67" strokeWidth="3" />
        {data.map((point, index) => {
          const x = left + (index / Math.max(data.length - 1, 1)) * plotWidth;
          const y = top + plotHeight - (point.occupancy / maxValue) * plotHeight;
          return <circle key={point.bucket} cx={x} cy={y} r="4" fill="#426f67" />;
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
      <p className="chart-description">Entries and exits grouped by recent time buckets.</p>
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
      <p className="chart-description">Accepted enters and leaves compared across doors.</p>
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
