# Dashboard Controls And Analytics

## Summary
Upgrade the room occupancy system so the dashboard becomes a real operator console instead of a raw event viewer. The change fixes live per-door analytics updates, adds richer charts and filtering, moves raw logs into a dedicated debug page, and introduces controls for pausing collection, choosing mock vs camera mode, and setting the initial counter value.

## Why
The current MVP proves the pipeline works, but the UI still feels too technical and too passive for a class demo. The dashboard should tell a clearer story with live statistics and charts, while also letting the operator control how the system runs during testing and presentation.

## Goals
- Fix the live analytics bug where per-door statistics lag until a page refresh.
- Replace the mostly raw dashboard with clearer plots, filters, and higher-level statistics.
- Move detailed retained logs into a dedicated debug-focused subpage.
- Add operator controls for:
  - start or stop event collection
  - choose the active source mode (`mock` or `camera`)
  - set the starting occupancy value
- Keep the controls and telemetry aligned with the IoT architecture rather than hard-coding UI-only behavior.

## Non-Goals
- Full authentication or multi-user permissions for the control panel.
- Production-grade orchestration of containers, processes, or remote devices.
- Perfect analytics for arbitrarily long historical datasets.
- Changing the core room-counting purpose of the system.

## Scope
This change touches the event model, subscriber API, publisher coordination behavior, and React frontend navigation and visualization. It adds a lightweight control plane on top of the current system so publishers and the subscriber can react to shared operational state, while preserving the existing occupancy flow and MQTT-based architecture.

## Success Criteria
- Live per-door analytics update immediately when new SSE events arrive, without requiring a page refresh.
- The main dashboard emphasizes charts, summaries, and filters rather than raw tables.
- A separate debug/log page exists for retained event inspection and troubleshooting.
- The operator can pause and resume collection from the UI, and paused mode prevents new events from changing occupancy or analytics.
- The operator can select between mock mode and camera mode from the UI, and only the chosen source is treated as active.
- The operator can set the baseline occupancy value before or during a demo.
- The system surfaces current control state clearly in both API responses and the UI.

## Risks
- Adding runtime controls can blur responsibility between publishers and subscriber if the control flow is not defined clearly.
- Live charts and analytics can drift if the SSE payload does not provide enough data for consistent updates.
- Source selection introduces event-routing questions for already-running publishers, so the behavior during mode switches needs to be explicit.
- The UI can become cluttered unless the main dashboard and debug tools are separated cleanly.

## Additional Ideas
- Show service health cards for broker, subscriber, and currently selected source.
- Track rejected/invalid events on the debug page for calibration and troubleshooting.
- Add session markers so a classroom demo can distinguish one measurement run from another.
- Add a one-click “reset to baseline” action for repeated demos.
