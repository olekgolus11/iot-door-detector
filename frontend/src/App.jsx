import { useEffect, useState } from "react";
import { OccupancyCard } from "./components/OccupancyCard";
import { EventFeed } from "./components/EventFeed";
import { EventTable } from "./components/EventTable";
import { SummaryPanel } from "./components/SummaryPanel";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [occupancy, setOccupancy] = useState(0);
  const [events, setEvents] = useState([]);
  const [historyEvents, setHistoryEvents] = useState([]);
  const [summary, setSummary] = useState({ total_enters: 0, total_leaves: 0, per_door: [] });
  const [status, setStatus] = useState("Connecting to live data...");
  const [filters, setFilters] = useState({ doorId: "", since: "" });

  async function loadHistory(active = true, nextFilters = filters) {
    const query = new URLSearchParams({ limit: "100" });
    if (nextFilters.doorId) {
      query.set("door_id", nextFilters.doorId);
    }
    if (nextFilters.since) {
      query.set("since", nextFilters.since);
    }

    const eventsRes = await fetch(`${API_URL}/api/events?${query.toString()}`);
    if (!active) {
      return;
    }

    const eventsPayload = await eventsRes.json();
    setHistoryEvents(eventsPayload.events ?? []);
  }

  useEffect(() => {
    let active = true;

    async function loadInitialData() {
      try {
        const [occupancyRes, eventsRes, summaryRes] = await Promise.all([
          fetch(`${API_URL}/api/occupancy`),
          fetch(`${API_URL}/api/events?limit=25`),
          fetch(`${API_URL}/api/summary`),
        ]);

        if (!active) {
          return;
        }

        const occupancyPayload = await occupancyRes.json();
        const eventsPayload = await eventsRes.json();
        const summaryPayload = await summaryRes.json();

        setOccupancy(occupancyPayload.occupancy ?? 0);
        setEvents(eventsPayload.events ?? []);
        setSummary(summaryPayload);
        await loadHistory(active, filters);
        setStatus("Live updates connected.");
      } catch (error) {
        setStatus("Waiting for the API. Start the subscriber service to see live data.");
      }
    }

    loadInitialData();

    const source = new EventSource(`${API_URL}/api/stream`);
    source.onmessage = (message) => {
      const payload = JSON.parse(message.data);
      if (payload.type === "snapshot") {
        setOccupancy(payload.occupancy ?? 0);
        setSummary(payload.summary ?? summary);
        return;
      }

      if (payload.type === "door_event") {
        setOccupancy(payload.occupancy ?? 0);
        setEvents((current) => [payload.event, ...current].slice(0, 50));
        setSummary((current) => ({
          ...current,
          occupancy: payload.occupancy ?? 0,
          total_enters:
            current.total_enters + (payload.event.direction === "enter" ? 1 : 0),
          total_leaves:
            current.total_leaves + (payload.event.direction === "leave" ? 1 : 0),
        }));
      }
      setStatus("Receiving live MQTT-backed updates.");
    };
    source.onerror = () => {
      setStatus("Realtime connection lost. Retrying SSE stream...");
    };

    return () => {
      active = false;
      source.close();
    };
  }, []);

  useEffect(() => {
    let active = true;

    loadHistory(active, filters).catch(() => {
      setStatus("Historical log filters are waiting for the API.");
    });

    return () => {
      active = false;
    };
  }, [filters]);

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">IoT Door Detector</p>
        <h1>Realtime room occupancy from MQTT doorway events</h1>
        <p className="hero-copy">
          This dashboard shows the current room count, a live feed of enter and leave events,
          and retained history from the central subscriber service.
        </p>
        <p className="status-pill">{status}</p>
      </section>

      <section className="dashboard-grid">
        <OccupancyCard occupancy={occupancy} />
        <SummaryPanel summary={summary} />
      </section>

      <section className="content-grid">
        <EventFeed events={events.slice(0, 8)} />
        <EventTable events={historyEvents} filters={filters} onFiltersChange={setFilters} />
      </section>
    </main>
  );
}
