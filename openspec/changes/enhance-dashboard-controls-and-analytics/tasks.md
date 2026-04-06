# Tasks: Dashboard Controls And Analytics

## 1. Add backend control-state support
- [x] Add SQLite persistence for control state and rejected-event records.
- [x] Add API models and validation for reading and updating control state.
- [x] Implement `GET /api/control-state` and `PUT /api/control-state`.
- [x] Update occupancy handling so baseline occupancy can be set explicitly.

## 2. Extend the event model and ingestion flow
- [x] Extend the shared event contract with `source_type` and `publisher_id`.
- [x] Update mock and YOLO publishers to emit the enriched event payload.
- [x] Gate accepted events in the subscriber based on `collection_enabled` and `active_source_mode`.
- [x] Persist rejected or ignored events with explicit reason codes for debugging.

## 3. Fix realtime analytics consistency
- [x] Update the subscriber summary logic so per-door analytics are always recomputed consistently.
- [x] Include refreshed summary and control-state data in SSE broadcasts.
- [x] Fix the frontend SSE handling so per-door totals update immediately without a manual refresh.

## 4. Expand analytics and chart APIs
- [x] Add summary endpoints or response shapes for occupancy timeline data.
- [x] Add entries-vs-leaves chart data grouped by time bucket.
- [x] Add per-door aggregated statistics suitable for bar or stacked charts.
- [x] Add richer event-list filters for door, direction, source type, and time range.

## 5. Redesign the frontend information architecture
- [x] Add routing for a main dashboard page and a dedicated debug/events page.
- [x] Move raw retained logs out of the landing dashboard.
- [x] Add a dashboard operator control panel for pause/resume, source selection, and baseline occupancy input.
- [x] Add chart components for occupancy trend, entries vs leaves, and per-door comparisons.
- [x] Add a compact recent-event preview on the main dashboard.

## 6. Build the debug and troubleshooting views
- [x] Add a retained-events table with the richer filter set.
- [x] Add a rejected-events table with reason codes.
- [x] Show current control state and recent system status on the debug page.

## 7. Verify behavior and polish the demo
- [x] Add backend tests for control-state persistence, gating logic, and enriched summary responses.
- [ ] Add frontend tests for per-door live updates, dashboard routing, and operator controls.
- [ ] Manually verify pause/resume behavior with mock publishers.
- [ ] Manually verify switching between mock mode and camera mode.
- [ ] Manually verify baseline occupancy changes and chart updates.
- [x] Update the setup and demo documentation with the new control and analytics workflow.
