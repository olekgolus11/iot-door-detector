# Design: IoT Room Occupancy System

## Current State
- The repository is currently an empty starter with OpenSpec configuration only.
- No Python services, MQTT broker configuration, persistence layer, or frontend application exist yet.
- The project requirements are known: computer-vision-based doorway detection, MQTT-based event flow, retained event logs, and a simple dashboard UI.

## Proposed Solution
Implement the system as a local multi-service demo with clear IoT boundaries:

1. A `publisher-yolo` Python service reads a phone IP camera stream, runs YOLO detection plus tracking, and publishes doorway crossing events.
2. One or more `publisher-mock` Python services generate semi-random events for development, testing, and demos without a camera.
3. An MQTT broker relays events from publishers to subscribers.
4. A `subscriber-api` Python service subscribes to door-event topics, validates and stores events in SQLite, maintains current occupancy, and exposes REST plus SSE APIs.
5. A React web UI displays the current occupancy, live feed, and historical logs.
6. Docker Compose orchestrates the broker, backend services, and frontend for a reproducible classroom setup.

## Architecture

### Event Model
- Use a single JSON event schema:
  - `timestamp`: ISO 8601 datetime in UTC
  - `door_id`: stable logical door identifier
  - `direction`: `enter` or `leave`
- Publish events to MQTT topics in the form `doors/<door_id>/events`.
- Subscribe centrally with `doors/+/events` so new doors can be added later without redesigning the topic contract.

### Publisher Services
- `publisher-yolo`
  - Input: phone IP camera stream exposed over RTSP or HTTP.
  - Pipeline: frame capture, YOLO person detection, object tracking, virtual line crossing, event emission.
  - Each tracked person should produce at most one event per crossing to reduce duplicate counts.
  - Expose configuration for stream URL, door ID, line coordinates, model variant, confidence threshold, and publish cadence.
- `publisher-mock`
  - Generates valid events on configurable intervals with semi-random enter/leave behavior.
  - Supports deterministic seeding for repeatable tests and demos.
  - Can simulate one or more doors even though the real pipeline starts with one camera.

### Broker
- Use Mosquitto as the local MQTT broker.
- Keep the broker setup intentionally simple for class use: no custom auth in v1, standard MQTT port, and Docker Compose-managed startup.

### Subscriber and API
- Consume MQTT door events, validate schema, and write accepted events to SQLite.
- Maintain a derived occupancy value based on event order:
  - `enter` increments occupancy by 1
  - `leave` decrements occupancy by 1 but clamps at 0
- Separate responsibilities into:
  - MQTT ingest
  - event validation/parsing
  - persistence
  - occupancy aggregation
  - HTTP and SSE delivery
- Expose API interfaces for:
  - current occupancy snapshot
  - historical event list with simple filters such as door and time range
  - lightweight summary analytics such as enters vs leaves by time bucket
  - SSE stream for new events and occupancy updates

### Web UI
- Use React for a simple dashboard-style interface.
- Load initial state over HTTP, then switch to SSE for live updates.
- Provide views for:
  - current occupancy counter
  - live incoming events
  - retained historical log table
  - basic analysis panel
- Keep the design simple and class-demo friendly rather than building a full admin tool.

### Deployment and Configuration
- Use Docker Compose for the default local topology.
- Treat services as separate containers where practical:
  - broker
  - subscriber/API
  - mock publisher
  - web UI
- Allow the YOLO publisher to run either in Compose or directly on the host machine if camera access and local dependencies make that easier during development.
- Configure all services through environment variables and documented defaults.

## Data and Interface Decisions
- SQLite is the persistence backend for v1 because it keeps setup simple while still supporting queries for logs and analytics.
- SSE is the browser-facing realtime transport because updates are server-to-client only and do not require WebSocket complexity.
- The first release supports one real camera feed, but the schema and topic layout are intentionally multi-door ready.
- Events are append-only. Occupancy is derived by replaying or incrementally applying ordered events rather than being authored directly by publishers.

## Error Handling and Operational Rules
- Reject malformed MQTT messages before they affect occupancy.
- Log and preserve ingestion errors separately from accepted events so debugging remains possible during demos.
- Prevent negative occupancy in the aggregator even if mock publishers or detection glitches emit extra `leave` events.
- Handle temporary broker disconnects in publishers and subscriber with reconnect logic and visible logging.
- Make the UI resilient to SSE disconnects by retrying and re-fetching the latest occupancy snapshot.

## Testing Strategy
- Unit-test event schema validation and occupancy aggregation rules.
- Unit-test mock publisher generation so emitted payloads always match the event contract.
- Integration-test MQTT broker to subscriber flow with sample messages and SQLite verification.
- Integration-test REST plus SSE behavior for current occupancy and live updates.
- Validate the YOLO publisher against recorded or live doorway footage to confirm line-crossing direction.
- Add an end-to-end smoke test path using mock publishers and the dashboard to verify the full demo stack.

## Open Questions Resolved For This Change
- Deployment topology: Docker Compose is the default demo environment.
- Persistence choice: SQLite is sufficient for retained logs and aggregated state in v1.
- Browser realtime transport: SSE is preferred over WebSockets or polling.
- Detection approach: tracking plus virtual line crossing is the intended counting method.
- Camera source: the real publisher will read a phone IP camera stream.
