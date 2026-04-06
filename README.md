# iot-door-detector

IoT study project for counting how many people are in a room by detecting doorway crossings, publishing those events over MQTT, aggregating them in Python, and showing the results in a React dashboard.

## Architecture
- `backend/publisher_yolo`: reads a phone IP camera stream and publishes `enter` or `leave` events.
- `backend/publisher_mock`: generates semi-random doorway events for local demos and testing.
- `backend/subscriber_api`: subscribes to MQTT, stores events in SQLite, computes occupancy, and serves REST plus SSE.
- `docker/mosquitto`: local MQTT broker configuration.
- `frontend`: React dashboard for realtime occupancy, live feed, and retained logs.

## Event Contract
Every doorway event is a JSON object:

```json
{
  "timestamp": "2026-04-06T18:00:00Z",
  "door_id": "door-a",
  "direction": "enter"
}
```

MQTT topics follow `doors/<door_id>/events`.

## Quick Start
### Backend only
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=. python3 -m backend.subscriber_api.main
```

In another terminal:

```bash
source .venv/bin/activate
PYTHONPATH=. python3 -m backend.publisher_mock.main
```

### Full demo with Docker Compose
```bash
docker compose up --build
```

The default services are:
- MQTT broker on `localhost:1883`
- Subscriber API on `http://localhost:8000`
- React dashboard on `http://localhost:5173`

## API Endpoints
- `GET /health`
- `GET /api/occupancy`
- `GET /api/events?limit=25&door_id=door-a`
- `GET /api/summary`
- `GET /api/stream`

## YOLO Publisher Setup
The YOLO publisher uses a phone IP camera stream together with YOLO tracking.

1. Install the heavier CV dependencies:
   ```bash
   pip install -r backend/requirements-yolo.txt
   ```
2. Set camera and calibration variables:
   ```bash
   export CAMERA_STREAM_URL="http://<phone-ip>:<port>/video"
   export DOOR_ID="door-a"
   export LINE_START="100,100"
   export LINE_END="540,100"
   export ENTER_WHEN="negative_to_positive"
   ```
3. Run the publisher:
   ```bash
   PYTHONPATH=. python3 -m backend.publisher_yolo.main
   ```

`LINE_START` and `LINE_END` define the virtual doorway line. `ENTER_WHEN` controls which side change counts as an `enter`.

## Testing
Run the unit tests with:

```bash
PYTHONPATH=. python3 -m unittest discover -s backend/tests
```

## Notes
- Occupancy is clamped at zero so bad `leave` events do not make the count negative.
- The first version is designed for one real camera feed, but the event contract and MQTT topics support multiple doors.
- The frontend source is included, but this shell currently does not have `node` installed, so frontend install/build still needs a Node-enabled environment.
