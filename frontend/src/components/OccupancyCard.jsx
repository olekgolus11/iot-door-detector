export function OccupancyCard({ occupancy }) {
  return (
    <article className="panel occupancy-panel">
      <p className="panel-label">Current occupancy</p>
      <div className="occupancy-value">{occupancy}</div>
      <p className="panel-note">Derived centrally from validated enter and leave events.</p>
    </article>
  );
}

