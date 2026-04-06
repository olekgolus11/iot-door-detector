# Backend Services

This folder contains the Python services for the IoT room occupancy demo.

## Dependency Approach
- `requirements.txt` installs the shared runtime needed for the subscriber API and mock publisher.
- `requirements-yolo.txt` extends the base runtime with the heavier computer-vision dependencies required by `publisher-yolo`.

## Services
- `subscriber_api`: subscribes to MQTT, stores events in SQLite, computes occupancy, and serves REST plus SSE endpoints.
- `publisher_mock`: generates semi-random `enter` and `leave` events for local testing.
- `publisher_yolo`: reads a phone IP camera stream, uses YOLO tracking, and publishes doorway crossing events.

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

