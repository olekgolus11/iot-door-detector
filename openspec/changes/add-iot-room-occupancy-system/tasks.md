# Tasks: IoT Room Occupancy System

## 1. Scaffold the project structure
- [x] Create the top-level workspace layout for Python services, the React web app, shared configuration, and Docker assets.
- [x] Choose and document the Python dependency management approach for backend services.
- [x] Add base application entrypoints and configuration loading for `publisher-yolo`, `publisher-mock`, and `subscriber-api`.
- [x] Add the React application scaffold with a minimal dashboard shell.

## 2. Define the shared event contract
- [x] Define the doorway event JSON schema with `timestamp`, `door_id`, and `direction`.
- [x] Implement shared validation/parsing logic in the subscriber so malformed MQTT payloads are rejected safely.
- [x] Document MQTT topic conventions and retained message expectations for publishers and subscriber.

## 3. Stand up the MQTT and local runtime environment
- [x] Add Docker Compose services for the broker, subscriber/API, mock publisher, and web UI.
- [x] Add Mosquitto configuration suitable for a local classroom demo.
- [x] Document required environment variables, local startup steps, and how to connect a phone IP camera stream.

## 4. Build the mock publisher path
- [x] Implement a mock event generator with configurable door IDs, intervals, randomness, and seed values.
- [x] Publish generated events to MQTT using the shared event contract.
- [x] Add a simple run mode for demos where mock traffic can drive the whole system without the real camera publisher.

## 5. Build the real YOLO publisher
- [x] Implement video capture from a phone IP camera stream.
- [x] Integrate YOLO person detection and tracking for doorway monitoring.
- [x] Add virtual line-crossing logic that maps track direction to `enter` or `leave` events.
- [x] Publish validated doorway events to MQTT with reconnect and logging behavior.
- [x] Add calibration settings for stream URL, line coordinates, confidence threshold, and door ID.

## 6. Build the subscriber and persistence layer
- [x] Implement MQTT subscription and event ingestion for `doors/+/events`.
- [x] Persist accepted events in SQLite.
- [x] Implement occupancy aggregation with zero-floor clamping and a clear ordering strategy.
- [x] Expose REST endpoints for current occupancy, historical logs, and simple summary analytics.
- [x] Expose an SSE stream for new events and occupancy updates.

## 7. Build the React dashboard
- [x] Display the current room occupancy prominently.
- [x] Show a live event feed driven by SSE.
- [x] Show retained logs with basic filtering by door and time.
- [x] Add a lightweight analysis view for historical event summaries.
- [x] Handle loading, empty, and reconnect states gracefully.

## 8. Verify and document the system
- [x] Add unit tests for event validation, occupancy aggregation, and mock event generation.
- [x] Add integration tests for MQTT ingestion, SQLite persistence, and SSE updates.
- [ ] Manually verify the end-to-end flow using mock publishers and the web UI.
- [ ] Manually verify the YOLO publisher against a phone stream or recorded footage.
- [x] Write setup and demo documentation covering architecture, startup, calibration, and troubleshooting.
