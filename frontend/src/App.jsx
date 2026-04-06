import { useEffect, useMemo, useState } from "react";
import { ShellNav } from "./components/ShellNav";
import { DashboardPage } from "./components/DashboardPage";
import { DebugPage } from "./components/DebugPage";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const emptySummary = {
  occupancy: 0,
  total_enters: 0,
  total_leaves: 0,
  per_door: [],
  entries_vs_leaves: [],
  occupancy_timeline: [],
  system_status: {
    accepted_events: 0,
    rejected_events: 0,
    collection_enabled: true,
    active_source_mode: "mock",
  },
  control_state: {
    collection_enabled: true,
    active_source_mode: "mock",
    baseline_occupancy: 0,
    baseline_updated_at: null,
    updated_at: null,
  },
};

const defaultFilters = {
  doorId: "",
  direction: "",
  sourceType: "",
  since: "",
  until: "",
};

function getRoute() {
  return window.location.hash === "#/debug/events" ? "debug" : "dashboard";
}

function buildQuery(filters, limit = 150) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (filters.doorId) query.set("door_id", filters.doorId);
  if (filters.direction) query.set("direction", filters.direction);
  if (filters.sourceType) query.set("source_type", filters.sourceType);
  if (filters.since) query.set("since", filters.since);
  if (filters.until) query.set("until", filters.until);
  return query.toString();
}

async function fetchJson(path) {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${path}`);
  }
  return response.json();
}

export default function App() {
  const [route, setRoute] = useState(getRoute);
  const [summary, setSummary] = useState(emptySummary);
  const [controlState, setControlState] = useState(emptySummary.control_state);
  const [recentEvents, setRecentEvents] = useState([]);
  const [debugEvents, setDebugEvents] = useState([]);
  const [rejectedEvents, setRejectedEvents] = useState([]);
  const [health, setHealth] = useState({ status: "booting" });
  const [statusText, setStatusText] = useState("Connecting to subscriber API...");
  const [controlStatus, setControlStatus] = useState("Control plane ready.");
  const [debugFilters, setDebugFilters] = useState(defaultFilters);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const syncRoute = () => setRoute(getRoute());
    window.addEventListener("hashchange", syncRoute);
    syncRoute();
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  useEffect(() => {
    let active = true;

    async function loadInitial() {
      try {
        const [summaryPayload, controlPayload, healthPayload, recentPayload] = await Promise.all([
          fetchJson("/api/summary"),
          fetchJson("/api/control-state"),
          fetchJson("/health"),
          fetchJson("/api/events?limit=8"),
        ]);

        if (!active) return;

        setSummary(summaryPayload);
        setControlState(controlPayload);
        setHealth(healthPayload);
        setRecentEvents(recentPayload.events ?? []);
        setStatusText("Live dashboard connected.");
      } catch (error) {
        if (active) {
          setStatusText("Waiting for the subscriber API. Start the backend to unlock live analytics.");
        }
      }
    }

    loadInitial();

    const source = new EventSource(`${API_URL}/api/stream`);
    source.onmessage = (message) => {
      const payload = JSON.parse(message.data);
      if (payload.summary) {
        setSummary(payload.summary);
      }
      if (payload.control_state) {
        setControlState(payload.control_state);
      }
      if (payload.event) {
        setRecentEvents((current) => [payload.event, ...current].slice(0, 8));
      }
      if (payload.rejected_event) {
        setRejectedEvents((current) => [payload.rejected_event, ...current].slice(0, 20));
      }
      setHealth((current) => ({
        ...current,
        status: "live",
        system_status: payload.summary?.system_status ?? current.system_status,
      }));
      setStatusText(
        payload.type === "control_state_updated"
          ? "Control state updated and broadcast live."
          : "Realtime analytics are flowing."
      );
      setRefreshKey((value) => value + 1);
    };
    source.onerror = () => {
      setStatusText("Realtime stream interrupted. Retrying SSE connection...");
    };

    return () => {
      active = false;
      source.close();
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadDebugData() {
      try {
        const [eventsPayload, rejectedPayload] = await Promise.all([
          fetchJson(`/api/events?${buildQuery(debugFilters, 150)}`),
          fetchJson(`/api/rejected-events?${buildQuery(debugFilters, 150)}`),
        ]);
        if (!active) return;
        setDebugEvents(eventsPayload.events ?? []);
        setRejectedEvents(rejectedPayload.events ?? []);
      } catch (error) {
        if (active) {
          setStatusText("Debug tables are waiting for the API.");
        }
      }
    }

    loadDebugData();
    return () => {
      active = false;
    };
  }, [debugFilters, refreshKey, route]);

  async function updateControlState(partial) {
    setControlStatus("Saving control changes...");
    try {
      const response = await fetch(`${API_URL}/api/control-state`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(partial),
      });
      if (!response.ok) {
        throw new Error("Unable to update control state");
      }
      const updated = await response.json();
      setControlState(updated);
      setControlStatus("Control state saved. Waiting for live snapshot...");
    } catch (error) {
      setControlStatus("Control update failed. Check whether the subscriber API is running.");
    }
  }

  const availableDoors = useMemo(
    () => summary.per_door.map((door) => door.door_id),
    [summary.per_door]
  );

  return (
    <main className="app-shell">
      <ShellNav route={route} statusText={statusText} />
      {route === "dashboard" ? (
        <DashboardPage
          summary={summary}
          controlState={controlState}
          recentEvents={recentEvents}
          controlStatus={controlStatus}
          health={health}
          onUpdateControlState={updateControlState}
        />
      ) : (
        <DebugPage
          summary={summary}
          controlState={controlState}
          filters={debugFilters}
          events={debugEvents}
          rejectedEvents={rejectedEvents}
          availableDoors={availableDoors}
          onFiltersChange={setDebugFilters}
        />
      )}
    </main>
  );
}
