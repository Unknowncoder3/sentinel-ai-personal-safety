import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./styles.css";

const API = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}, token) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const form = new URLSearchParams({ username: email.trim(), password });
      const response = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: form,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to sign in");
      localStorage.setItem("sentinel_token", data.access_token);
      onLogin(data.access_token);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <main className="auth-shell"><section className="auth-card">
    <div className="brand-mark">S</div><p className="eyebrow">SENTINEL AI</p>
    <h1>Personal safety command center</h1>
    <p className="muted">Sign in to monitor your enrolled devices and safety status.</p>
    <form onSubmit={submit} className="stack">
      <label>Email<input value={email} onChange={e => setEmail(e.target.value)} type="email" required /></label>
      <label>Password<input value={password} onChange={e => setPassword(e.target.value)} type="password" required /></label>
      {error && <div className="error">{error}</div>}
      <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    </form><small className="muted">API: {API}</small>
  </section></main>;
}

function MapPanel({ location, journeyPoints = [], journey }) {
  const mapRef = React.useRef(null); const map = React.useRef(null); const marker = React.useRef(null); const trail = React.useRef(null);
  useEffect(() => {
    if (!mapRef.current || map.current) return;
    map.current = L.map(mapRef.current).setView([20.5937, 78.9629], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap contributors" }).addTo(map.current);
    return () => map.current?.remove();
  }, []);
  useEffect(() => {
    if (!map.current) return;
    if (trail.current) { trail.current.remove(); trail.current = null; }
    const points = journeyPoints.map(p => [p.latitude, p.longitude]);
    if (points.length > 1) trail.current = L.polyline(points, { weight: 4 }).addTo(map.current);
  }, [journeyPoints]);
  useEffect(() => {
    if (!map.current || !location) return;
    const point = [location.latitude, location.longitude];
    if (!marker.current) marker.current = L.marker(point).addTo(map.current); else marker.current.setLatLng(point);
    marker.current.bindPopup(`<b>${journey ? "Journey location" : "Latest device location"}</b><br>${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`).openPopup();
    map.current.setView(point, 16);
  }, [location, journey]);
  return <div ref={mapRef} className="map" />;
}

function JourneyPanel({ token, selectedDevice, latest, onError }) {
  const [journeys, setJourneys] = useState([]);
  const [activeJourney, setActiveJourney] = useState(null);
  const [journeyPoints, setJourneyPoints] = useState([]);
  const [destination, setDestination] = useState("");
  const [eta, setEta] = useState("");
  const [busy, setBusy] = useState(false);
  const [journeyStatus, setJourneyStatus] = useState("Ready");

  async function loadJourneys() {
    const data = await request("/api/v1/journeys", {}, token);
    setJourneys(data);
    const active = data.find(item => item.status === "active");
    setActiveJourney(active || null);
  }

  async function loadPoints(journeyId) {
    if (!journeyId) return;
    const data = await request(`/api/v1/journeys/${journeyId}/points`, {}, token);
    setJourneyPoints(data);
  }

  useEffect(() => { loadJourneys().catch(err => onError(err.message)); }, [token]);
  useEffect(() => {
    if (!activeJourney) { setJourneyPoints([]); return; }
    loadPoints(activeJourney.id).catch(err => onError(err.message));
    const timer = setInterval(async () => {
      try {
        const refreshed = await request(`/api/v1/journeys/${activeJourney.id}`, {}, token);
        setActiveJourney(refreshed);
        await loadPoints(activeJourney.id);
      } catch (_) {}
    }, 10000);
    return () => clearInterval(timer);
  }, [activeJourney?.id, token]);

  function getBrowserPosition() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) return reject(new Error("Browser geolocation is not available"));
      navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 });
    });
  }

  async function startJourney() {
    if (!selectedDevice) return onError("Pair/select a device first");
    if (!destination.trim() || !eta) return onError("Enter a destination and ETA");
    setBusy(true); setJourneyStatus("Getting current location…");
    try {
      let latitude = latest?.latitude ?? null;
      let longitude = latest?.longitude ?? null;
      if (latitude == null || longitude == null) {
        const position = await getBrowserPosition();
        latitude = position.coords.latitude; longitude = position.coords.longitude;
      }
      const created = await request("/api/v1/journeys", {
        method: "POST",
        body: JSON.stringify({
          device_id: selectedDevice.id,
          destination: destination.trim(),
          start_latitude: latitude,
          start_longitude: longitude,
          end_latitude: null,
          end_longitude: null,
          eta: new Date(eta).toISOString(),
        }),
      }, token);
      setActiveJourney(created);
      setJourneys(prev => [created, ...prev.filter(item => item.id !== created.id)]);
      setJourneyStatus("Journey active — location updates can be sent below");
      setDestination(""); setEta("");
      await sendPoint(created, latitude, longitude);
    } catch (err) { onError(err.message); setJourneyStatus("Unable to start journey"); }
    finally { setBusy(false); }
  }

  async function sendPoint(journey = activeJourney, latitude = null, longitude = null) {
    if (!journey) return;
    setBusy(true);
    try {
      if (latitude == null || longitude == null) {
        const position = await getBrowserPosition();
        latitude = position.coords.latitude; longitude = position.coords.longitude;
      }
      const point = await request(`/api/v1/journeys/${journey.id}/points`, {
        method: "POST",
        body: JSON.stringify({ latitude, longitude, speed_mps: null, bearing: null, battery_level: null, recorded_at: new Date().toISOString() }),
      }, token);
      setJourneyPoints(prev => [...prev, point]);
      const refreshed = await request(`/api/v1/journeys/${journey.id}`, {}, token);
      setActiveJourney(refreshed);
      setJourneyStatus(`Location sent at ${new Date().toLocaleTimeString()}`);
    } catch (err) { onError(err.message); }
    finally { setBusy(false); }
  }

  async function completeJourney() {
    if (!activeJourney) return;
    setBusy(true);
    try {
      const completed = await request(`/api/v1/journeys/${activeJourney.id}/complete`, { method: "POST" }, token);
      setJourneys(prev => prev.map(item => item.id === completed.id ? completed : item));
      setActiveJourney(null); setJourneyPoints([]); setJourneyStatus("Journey completed");
    } catch (err) { onError(err.message); }
    finally { setBusy(false); }
  }

  return <section className="journey-section">
    <div className="card journey-card">
      <div className="journey-header"><div><p className="eyebrow">SAFE JOURNEY MODE</p><h3>Plan and monitor a journey</h3><p className="muted">Use your browser location or the latest enrolled-device location. Tracking is user initiated.</p></div>{activeJourney && <span className="journey-live">● JOURNEY ACTIVE</span>}</div>
      {!activeJourney ? <div className="journey-form">
        <label>Destination<input value={destination} onChange={e => setDestination(e.target.value)} placeholder="e.g. Home, College, Airport" /></label>
        <label>Expected arrival<input value={eta} onChange={e => setEta(e.target.value)} type="datetime-local" /></label>
        <button disabled={busy || !selectedDevice} onClick={startJourney}>{busy ? "Starting…" : "▶ Start Safe Journey"}</button>
      </div> : <>
        <div className="journey-summary">
          <div><span>Destination</span><strong>{activeJourney.destination}</strong></div>
          <div><span>Risk score</span><strong className={activeJourney.risk_score >= 60 ? "risk-high" : activeJourney.risk_score >= 30 ? "risk-medium" : "risk-low"}>{activeJourney.risk_score}/100</strong></div>
          <div><span>ETA</span><strong>{new Date(activeJourney.eta).toLocaleString()}</strong></div>
          <div><span>Points</span><strong>{journeyPoints.length}</strong></div>
        </div>
        <div className="journey-actions"><button disabled={busy} onClick={() => sendPoint()}>{busy ? "Updating…" : "📍 Send Current Location"}</button><button className="secondary" disabled={busy} onClick={completeJourney}>✓ Complete Journey</button></div>
        <p className="journey-status">{journeyStatus}</p>
        <div className="journey-map"><MapPanel location={journeyPoints[journeyPoints.length - 1] || latest} journeyPoints={journeyPoints} journey={activeJourney} /></div>
      </>}
    </div>
    {journeys.length > 0 && <div className="card journey-history"><div className="section-title"><span>Journey history</span><span className="muted">{journeys.length} journeys</span></div>{journeys.slice(0, 5).map(item => <div className="journey-row" key={item.id}><div><strong>{item.destination}</strong><small>{new Date(item.created_at).toLocaleString()} · {item.status}</small></div><span className="journey-score">{item.risk_score}/100</span></div>)}</div>}
  </section>;
}

function Dashboard({ token, onLogout }) {
  const [user, setUser] = useState(null), [devices, setDevices] = useState([]), [selected, setSelected] = useState("");
  const [locations, setLocations] = useState([]), [sosEvents, setSosEvents] = useState([]), [guardians, setGuardians] = useState([]);
  const [error, setError] = useState(""), [loading, setLoading] = useState(true), [actionBusy, setActionBusy] = useState("");
  const selectedDevice = useMemo(() => devices.find(d => d.id === selected), [devices, selected]);
  const latest = locations[0] || (selectedDevice?.last_latitude != null ? { latitude: selectedDevice.last_latitude, longitude: selectedDevice.last_longitude, battery_level: selectedDevice.battery_level, recorded_at: selectedDevice.last_seen_at } : null);
  const activeSOS = sosEvents.find(event => event.status !== "resolved");

  async function loadDevices() { const data = await request("/api/v1/devices", {}, token); setDevices(data); setSelected(current => current || data[0]?.id || ""); }
  async function loadLocations(deviceId) {
    if (!deviceId) return;
    const data = await request(`/api/v1/devices/${deviceId}/locations?limit=100`, {}, token);
    setLocations([...data].sort((a, b) => new Date(b.recorded_at || b.received_at) - new Date(a.recorded_at || a.received_at)));
  }
  async function loadSafety() {
    const [sos, guardianList] = await Promise.all([request("/api/v1/safety/sos", {}, token), request("/api/v1/safety/guardians", {}, token)]);
    setSosEvents(sos); setGuardians(guardianList);
  }
  async function safetyAction(eventId, action) {
    setActionBusy(eventId);
    try { await request(`/api/v1/safety/sos/${eventId}/${action}`, { method: "POST" }, token); await loadSafety(); }
    catch (err) { setError(err.message); } finally { setActionBusy(""); }
  }

  useEffect(() => { (async () => { try { setLoading(true); setUser(await request("/api/v1/auth/me", {}, token)); await Promise.all([loadDevices(), loadSafety()]); } catch (err) { setError(err.message); } finally { setLoading(false); } })(); }, [token]);
  useEffect(() => { if (!selected) return; loadLocations(selected).catch(err => setError(err.message)); const timer = setInterval(() => { loadLocations(selected).catch(() => {}); loadSafety().catch(() => {}); }, 10000); return () => clearInterval(timer); }, [selected]);
  if (loading) return <div className="loading">Loading Sentinel…</div>;

  return <main className="dashboard">
    <header className="topbar"><div><p className="eyebrow">SENTINEL AI</p><h2>Safety command center</h2></div><div className="top-actions"><span className="status-dot" /> {user?.name || user?.email || "Account"}<button className="ghost" onClick={onLogout}>Sign out</button></div></header>
    {error && <div className="error banner">{error}</div>}
    {activeSOS && <section className="sos-alert"><div><span className="sos-badge">EMERGENCY SOS</span><h3>{activeSOS.status === "acknowledged" ? "SOS acknowledged" : "Immediate attention required"}</h3><p>{activeSOS.message || "An emergency SOS was activated."}</p><small>{new Date(activeSOS.created_at).toLocaleString()} · {activeSOS.latitude?.toFixed(5)}, {activeSOS.longitude?.toFixed(5)}</small></div><div className="sos-actions"><button disabled={actionBusy === activeSOS.id || activeSOS.status === "acknowledged"} onClick={() => safetyAction(activeSOS.id, "acknowledge")}>{actionBusy === activeSOS.id ? "Updating…" : "Acknowledge"}</button><button className="secondary" disabled={actionBusy === activeSOS.id} onClick={() => safetyAction(activeSOS.id, "resolve")}>Resolve</button></div></section>}
    <section className="grid">
      <aside className="sidebar card">
        <div className="section-title"><span>Enrolled devices</span><span className="count">{devices.length}</span></div>
        {devices.length === 0 ? <p className="muted">No device paired yet. Pair a phone from the Sentinel Android app.</p> : devices.map(device => <button key={device.id} className={`device ${selected === device.id ? "active" : ""}`} onClick={() => setSelected(device.id)}><span className="device-icon">⌁</span><span><strong>{device.name}</strong><small>{device.platform} · {device.is_online ? "Online" : "Offline"}</small></span></button>)}
        <div className="sidebar-divider" /><div className="section-title"><span>Trusted guardians</span><span className="count">{guardians.length}</span></div>
        {guardians.length === 0 ? <p className="muted">No guardians configured.</p> : guardians.map(g => <div className="guardian" key={g.id}><strong>{g.name}</strong><small>{g.phone}{g.email ? ` · ${g.email}` : ""}</small></div>)}
      </aside>
      <section className="content">
        <div className="stats">
          <div className="card stat"><span>Device</span><strong>{selectedDevice?.name || "—"}</strong><small>{selectedDevice?.device_identifier || "No selection"}</small></div>
          <div className="card stat"><span>Connection</span><strong>{selectedDevice ? (selectedDevice.is_online ? "Online" : "Offline") : "—"}</strong><small>{selectedDevice?.last_seen_at ? new Date(selectedDevice.last_seen_at).toLocaleString() : "No signal yet"}</small></div>
          <div className="card stat"><span>Battery</span><strong>{latest?.battery_level != null ? `${Math.round(latest.battery_level)}%` : "—"}</strong><small>Latest reported level</small></div>
          <div className={`card stat ${activeSOS ? "danger-stat" : ""}`}><span>Safety status</span><strong>{activeSOS ? "SOS ACTIVE" : "All clear"}</strong><small>{sosEvents.length} recorded SOS events</small></div>
        </div>
        <JourneyPanel token={token} selectedDevice={selectedDevice} latest={latest} onError={setError} />
        <div className="card map-card"><div className="map-header"><div><h3>Live location</h3><p className="muted">Polling every 10 seconds while this dashboard is open.</p></div>{latest && <span className="live-pill">● LIVE</span>}</div><MapPanel location={latest} /></div>
        <div className="card timeline"><div className="section-title"><span>Location timeline</span><span className="muted">{selectedDevice?.name || "Select a device"}</span></div>{locations.length === 0 ? <p className="muted empty">No location records received yet.</p> : locations.slice(0, 8).map(item => <div className="timeline-row" key={item.id}><span className="timeline-dot" /><div><strong>{item.latitude.toFixed(5)}, {item.longitude.toFixed(5)}</strong><small>{new Date(item.recorded_at || item.received_at).toLocaleString()} · ±{item.accuracy_m ? Math.round(item.accuracy_m) : "—"}m</small></div></div>)}</div>
        <div className="card timeline"><div className="section-title"><span>Recent safety events</span><span className="muted">Last {sosEvents.length}</span></div>{sosEvents.length === 0 ? <p className="muted empty">No SOS events recorded.</p> : sosEvents.slice(0, 6).map(event => <div className="safety-row" key={event.id}><div><strong>{event.status.toUpperCase()}</strong><small>{new Date(event.created_at).toLocaleString()} · {event.message || "Emergency event"}</small></div>{event.status !== "resolved" && <div><button className="mini" onClick={() => safetyAction(event.id, "acknowledge")} disabled={actionBusy === event.id || event.status === "acknowledged"}>Ack</button><button className="mini secondary" onClick={() => safetyAction(event.id, "resolve")} disabled={actionBusy === event.id}>Resolve</button></div>}</div>)}</div>
      </section>
    </section>
  </main>;
}

function App() { const [token, setToken] = useState(localStorage.getItem("sentinel_token")); if (!token) return <Login onLogin={setToken} />; return <Dashboard token={token} onLogout={() => { localStorage.removeItem("sentinel_token"); setToken(null); }} />; }
createRoot(document.getElementById("root")).render(<App />);
