# Design: Dashboard Controls And Analytics

## Current State
- The main dashboard mixes live highlights and raw retained logs on a single page.
- The analysis panel updates total enters and leaves in realtime, but per-door values stay stale until data is re-fetched.
- The subscriber exposes occupancy, events, summary, and SSE endpoints, but there is no operator control API.
- Publishers run independently and cannot react to a shared control state such as “paused” or “mock-only.”

## Proposed Solution
Treat this as a combined observability and control upgrade:

1. Extend the backend with a persisted control state for collection status, active source mode, and baseline occupancy.
2. Extend publishers and subscriber behavior so the selected control state affects which events are accepted and applied.
3. Enrich SSE payloads and summary APIs so the dashboard can update analytics consistently in realtime.
4. Redesign the React UI into two routes:
   - main dashboard for charts, KPIs, and operator controls
   - debug page for raw retained logs and troubleshooting views

## Architecture

### Control Plane
- Add a persisted control-state record in SQLite with:
  - `collection_enabled`: boolean
  - `active_source_mode`: `mock` or `camera`
  - `baseline_occupancy`: integer
  - `updated_at`: timestamp
- Expose control endpoints:
  - `GET /api/control-state`
  - `PUT /api/control-state`
- `PUT /api/control-state` supports:
  - toggling collection on or off
  - switching active source mode
  - setting or resetting the baseline occupancy
- When baseline occupancy changes, the subscriber updates the derived occupancy state immediately without rewriting historical events.

### Event Model Changes
- Extend doorway events with optional metadata:
  - `source_type`: `mock` or `camera`
  - `publisher_id`: logical publisher identifier
- Keep `timestamp`, `door_id`, and `direction` as the core required fields.
- For compatibility, the subscriber may accept missing metadata and treat it as `unknown`, but all in-repo publishers should emit the enriched event shape after this change.

### Subscriber Behavior
- Centralize gating inside the subscriber so control behavior remains authoritative:
  - if `collection_enabled` is `false`, incoming events are stored in a rejected/debug channel or ignored with an explicit reason, but they do not change occupancy
  - if an event’s `source_type` does not match `active_source_mode`, it is ignored for occupancy and analytics
- The subscriber should broadcast a richer SSE payload for every accepted control or event update:
  - current occupancy
  - refreshed totals
  - refreshed per-door summary
  - current control state
- Add summary endpoints for chart-friendly data:
  - occupancy timeline buckets
  - entries vs leaves by time bucket
  - per-door totals
- Add debug endpoints for:
  - retained raw events with filters
  - rejected/ignored events with reasons

### Publisher Behavior
- `publisher-mock` adds `source_type=mock` and a stable `publisher_id`.
- `publisher-yolo` adds `source_type=camera` and a stable `publisher_id`.
- Publishers do not need to fully self-orchestrate mode changes in v1; the subscriber remains the authority by filtering events based on control state.
- As a small usability improvement, publishers may optionally subscribe to a control topic later to display their current mode, but that is not required for this change.

### Frontend Information Architecture
- Use routing with two pages:
  - `/` dashboard
  - `/debug/events` raw logs and rejected-event inspection
- Main dashboard sections:
  - occupancy hero card
  - operator control panel
  - live KPI cards
  - occupancy-over-time chart
  - entries vs leaves chart
  - per-door comparison chart
  - compact recent-event preview
- Debug page sections:
  - raw retained event table
  - rejected-event table
  - filters for door, direction, source type, and time range

### Frontend State Strategy
- Load an initial snapshot from REST.
- Keep dashboard state fresh through SSE messages that already include updated summary and control-state payloads.
- Fix the current per-door bug by updating summary state from server-provided per-door data rather than only incrementing top-level totals on the client.
- Use a chart library suited to React dashboards, such as `recharts`, for quick implementation of line and bar charts.

## UX Decisions
- The main dashboard should prioritize comprehension:
  - big occupancy number
  - visible current mode
  - clear “collecting” vs “paused” state
  - charts that show trend, not just raw rows
- Raw event tables belong on the debug page, not the landing view.
- Changing baseline occupancy should require a deliberate form input rather than a hidden reset action.
- When collection is paused, the dashboard should show a visible paused banner and stop implying that live analytics are moving.
- Filters should be fast and practical:
  - door ID
  - direction
  - source type
  - time range

## Error Handling
- Invalid control-state updates should return clear 4xx responses.
- SSE reconnect should rehydrate the full summary and control state.
- Mode switches should not retroactively rewrite history; they only affect future event acceptance.
- Rejected events should be retained with a reason code so debugging and calibration stay possible.

## Testing Strategy
- Unit-test control-state validation and persistence.
- Unit-test subscriber event gating for paused mode and source-mode mismatch.
- Unit-test enriched summary generation, especially per-door realtime updates.
- Integration-test control-state updates through the API and verify SSE broadcasts carry the refreshed summary.
- Add frontend tests for:
  - route navigation between dashboard and debug page
  - per-door summary live updates
  - control panel interactions
  - filter behavior on the debug page

## Open Questions Resolved For This Change
- Control authority lives in the subscriber, not in the frontend alone.
- Source selection is enforced by event gating in the subscriber, not by trying to start and stop containers from the browser.
- Baseline occupancy is an operator-defined control-state value, not a synthetic event inserted into history.
- Rich analytics belong on the main dashboard, while raw logs move to a debug route.
