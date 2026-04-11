import { useEffect, useState } from "react";

export function ControlPanel({ controlState, onUpdateControlState, onClearDatabase, status }) {
  const [baselineInput, setBaselineInput] = useState(String(controlState.baseline_occupancy ?? 0));
  const [confirmingClear, setConfirmingClear] = useState(false);

  useEffect(() => {
    setBaselineInput(String(controlState.baseline_occupancy ?? 0));
  }, [controlState.baseline_occupancy]);

  return (
    <article className="panel control-panel">
      <div className="panel-header">
        <h2>Operator controls</h2>
        <span>{status}</span>
      </div>

      <div className="control-grid">
        <section className="control-section">
          <p className="panel-label">Collection state</p>
          <div className="segmented">
            <button
              type="button"
              className={controlState.collection_enabled ? "active" : ""}
              onClick={() => onUpdateControlState({ collection_enabled: true })}
            >
              Collecting
            </button>
            <button
              type="button"
              className={!controlState.collection_enabled ? "active" : ""}
              onClick={() => onUpdateControlState({ collection_enabled: false })}
            >
              Paused
            </button>
          </div>
        </section>

        <section className="control-section">
          <p className="panel-label">Active source</p>
          <div className="segmented">
            <button
              type="button"
              className={controlState.active_source_mode === "mock" ? "active" : ""}
              onClick={() => onUpdateControlState({ active_source_mode: "mock" })}
            >
              Test publishers
            </button>
            <button
              type="button"
              className={controlState.active_source_mode === "camera" ? "active" : ""}
              onClick={() => onUpdateControlState({ active_source_mode: "camera" })}
            >
              Camera program
            </button>
          </div>
          <p className="control-help">
            Camera mode pauses the mock publisher; test publisher mode resumes it.
          </p>
        </section>

        <section className="control-section baseline-section">
          <p className="panel-label">Baseline occupancy</p>
          <form
            className="baseline-form"
            onSubmit={(event) => {
              event.preventDefault();
              onUpdateControlState({ baseline_occupancy: Number(baselineInput || 0) });
            }}
          >
            <input
              type="number"
              min="0"
              value={baselineInput}
              onChange={(event) => setBaselineInput(event.target.value)}
            />
            <button type="submit">Apply baseline</button>
          </form>
        </section>

        <section className="control-section clear-database-section">
          <div>
            <p className="panel-label">Demo reset</p>
            <p className="control-help">
              Clears accepted, rejected, and ingest-error records while keeping source and collection settings.
            </p>
          </div>
          {confirmingClear ? (
            <div className="clear-confirm-row">
              <button
                type="button"
                className="clear-confirm-button"
                onClick={() => {
                  setConfirmingClear(false);
                  onClearDatabase();
                }}
              >
                Confirm clear
              </button>
              <button
                type="button"
                className="clear-cancel-button"
                onClick={() => setConfirmingClear(false)}
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="clear-database-button"
              onClick={() => setConfirmingClear(true)}
            >
              Clear database
            </button>
          )}
        </section>
      </div>
    </article>
  );
}
