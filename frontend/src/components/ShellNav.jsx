export function ShellNav({ route, statusText }) {
  return (
    <header className="shell-nav">
      <div>
        <p className="eyebrow">IoT Door Detector</p>
        <h1>Operator room console</h1>
      </div>
      <div className="nav-actions">
        <nav className="nav-pills">
          <a href="#/" className={route === "dashboard" ? "active" : ""}>
            Dashboard
          </a>
          <a href="#/debug/events" className={route === "debug" ? "active" : ""}>
            Debug events
          </a>
        </nav>
        <p className="status-pill">{statusText}</p>
      </div>
    </header>
  );
}
