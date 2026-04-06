# IoT Room Occupancy System

## Summary
Build a study project that counts how many people are currently in a room by detecting `enter` and `leave` events at a doorway, transmitting those events through MQTT, aggregating them in a central Python service, and presenting the results in a React web UI.

## Why
The project needs to demonstrate both practical computer vision and an IoT-style event architecture for class. A room counter based on doorway crossings is concrete enough for a demo, while MQTT publishers, a broker, retained logs, and a live dashboard show how distributed IoT systems exchange and consume sensor events.

## Goals
- Detect doorway crossings from a real phone camera stream using YOLO-based person detection.
- Publish doorway events from both a real publisher and semi-random mock publishers over MQTT.
- Store all received events and maintain the current room occupancy in a central subscriber service.
- Provide a React website with realtime occupancy, live event feed, and retained logs for later analysis.
- Package the system so it can be run locally as a multi-service demo.

## Non-Goals
- Supporting multiple real camera feeds in the first version.
- Building a production-grade identity, security, or access-control system.
- Creating advanced analytics beyond basic filtering, history, and occupancy summaries.
- Handling perfect counting accuracy in crowded or occluded doorway scenarios.

## Scope
The change covers one local end-to-end system made of a broker, Python publishers, a Python subscriber/API service, SQLite persistence, and a React frontend. The first version supports one real door/camera stream plus any number of mock publishers. The event format and MQTT topic layout stay compatible with future multi-door expansion.

## Success Criteria
- A real publisher can read a phone IP camera stream and emit `enter` and `leave` events when tracked people cross a configured doorway line.
- Mock publishers can generate valid test events without the real camera pipeline.
- The subscriber stores every event with timestamp, door ID, and direction, and updates a room occupancy counter that never drops below zero.
- The web UI shows the current occupancy in realtime and exposes retained historical logs for inspection.
- The project can be demonstrated locally with Docker Compose and documented setup steps.

## Risks
- Accurate direction detection depends on stable tracking and camera placement above the doorway.
- YOLO inference may be too heavy for some laptops unless model size and frame rate are tuned carefully.
- Event duplication or out-of-order delivery could skew occupancy if publisher and subscriber behavior are not made idempotent enough for the demo.
- Integrating Python services, MQTT, SQLite, and React adds enough moving parts that packaging and documentation need to be part of the implementation work, not an afterthought.
