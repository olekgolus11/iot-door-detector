# Backend Services

This folder contains the Python services for the IoT room occupancy demo.

## Dependency Approach
- `requirements.txt` installs the shared runtime needed for the subscriber API and mock publisher.
- `requirements-yolo.txt` extends the base runtime with the heavier computer-vision dependencies required by `publisher-yolo`.

## Services
- `subscriber_api`: subscribes to MQTT, stores accepted and rejected events in SQLite, applies operator control state, computes occupancy, and serves REST plus SSE endpoints.
- `publisher_mock`: generates semi-random `enter` and `leave` events for local testing.
- `publisher_yolo`: reads a phone IP camera stream, uses YOLO tracking, and publishes doorway crossing events.

## Control State
The subscriber keeps a persisted control state with:
- `collection_enabled`
- `active_source_mode`
- `baseline_occupancy`

Incoming events are gated centrally by this state, so:
- paused collection does not change occupancy
- events from the inactive source mode are retained as rejected debug records
- baseline occupancy can be reset directly for demos

## Run Locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=. python3 -m backend.subscriber_api.main
```

For the YOLO publisher:

```bash
pip install -r backend/requirements-yolo.txt
PYTHONPATH=. python3 -m backend.publisher_yolo.main
```

For camera calibration, the YOLO publisher supports:
- `LINE_START` and `LINE_END` for the virtual doorway line
- `LINE_BAND_PIXELS` for a wider crossing zone
- `YOLO_CROSSING_POINT=center` to track the middle of the person box
- `YOLO_CROSSING_POINT=bottom_center` to track the feet position instead
- `TRACK_COOLDOWN_FRAMES` to avoid duplicate events from one crossing
- `YOLO_TRACKER=botsort.yaml` to choose the Ultralytics tracker config
- `TRACK_LOST_GRACE_FRAMES` to recover a person after a short YOLO id drop
- `TRACK_MATCH_MAX_DISTANCE_PIXELS` to limit how far a recovered id may jump
- `TRACK_EVENT_SUPPRESSION_FRAMES` to suppress duplicate events after one physical crossing

The recovery settings are tuned for one person crossing at a time. They greatly reduce missed
events from brief tracking drops, but crowded or heavily occluded scenes still need better camera
placement or an additional sensor for near-perfect counting.

## Useful API Endpoints
- `GET /api/control-state`
- `PUT /api/control-state`
- `GET /api/events`
- `GET /api/rejected-events`
- `GET /api/summary`
- `GET /api/stream`
