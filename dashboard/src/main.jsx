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
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to sign in");
      localStorage.setItem("sentinel_token", data.access_token);
      onLogin(data.access_token);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return <main className="auth-shell">
    <section className="auth-card">
      <div className="brand-mark">S</div>
      <p className="eyebrow">SENTINEL AI</p>
      <h1>Personal safety command center</h1>
      <p className="muted">Sign in to monitor your enrolled devices and safety status.</p>
      <form onSubmit={submit} className="stack">
        <label>Email<input value={email} onChange={e => setEmail(e.target.value)} type="email" required /></label>
        <label>Password<input value={password} onChange={e => setPassword(e.target.value)} type="password" required /></label>
        {error && <div className="error">{error}</div>}
        <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
      <small className="muted">API: {API}</small>
    </section>
  </main>;
}

function MapPanel({ location }) {
  const mapRef = React.useRef(null);
  const map = React.useRef(null);
  const marker = React.useRef(null);

  useEffect(() => {
    if (!mapRef.current || map.current) return;
    map.current = L.map(mapRef.current).setView([20.5937, 78.9629], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map.current);
    return () => map.current?.remove();
  }, []);

  useEffect(() => {
    if (!map.current || !location) return;
    const point = [location.latitude, location.longitude];
    if (!marker.current) marker.current = L.marker(point).addTo(map.current);
    else marker.current.setLatLng(point);
    marker.current.bindPopup(`<b>Latest device location</b><br>${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`).openPopup();
    map.current.setView(point, 16);
  }, [location]);

  return <div ref={mapRef} className="map" />;
}

function Dashboard({ token, onLogout }) {
  const [user, setUser] = useState(null);
  const [devices, setDevices] = useState([]);
  const [selected, setSelected] = useState("");
  const [locations, setLocations] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const selectedDevice = useMemo(() => devices.find(d => d.id === selected), [devices, selected]);
  const latest = locations[0] || (selectedDevice?.last_latitude != null ? {
    latitude: selectedDevice.last_latitude,
    longitude: selectedDevice.last_longitude,
    battery_level: selectedDevice.battery_level,
    recorded_at: selectedDevice.last_seen_at,
  } : null);

  async function loadDevices() {
    const data = await request("/api/v1/devices", {}, token);
    setDevices(data);
    setSelected(current => current || data[0]?.id || "");
  }

  async function loadLocations(deviceId) {
    if (!deviceId) return;
    const data = await request(`/api/v1/devices/${deviceId}/locations?limit=100`, {}, token);
    setLocations([...data].sort((a, b) => new Date(b.recorded_at || b.received_at) - new Date(a.recorded_at || a.received_at)));
  }

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setUser(await request("/api/v1/auth/me", {}, token));
        await loadDevices();
      } catch (err) { setError(err.message); }
      finally { setLoading(false); }
    })();
  }, [token]);

  useEffect(() => {
    if (!selected) return;
    loadLocations(selected).catch(err => setError(err.message));
    const timer = setInterval(() => loadLocations(selected).catch(() => {}), 10000);
    return () => clearInterval(timer);
  }, [selected]);

  if (loading) return <div className="loading">Loading Sentinel…</div>;

  return <main className="dashboard">
    <header className="topbar">
      <div><p className="eyebrow">SENTINEL AI</p><h2>Safety command center</h2></div>
      <div className="top-actions"><span className="status-dot" /> {user?.name || user?.email || "Account"}<button className="ghost" onClick={onLogout}>Sign out</button></div>
    </header>
    {error && <div className="error banner">{error}</div>}
    <section className="grid">
      <aside className="sidebar card">
        <div className="section-title"><span>Enrolled devices</span><span className="count">{devices.length}</span></div>
        {devices.length === 0 ? <p className="muted">No device paired yet. Pair a phone from the Sentinel Android app.</p> : devices.map(device =>
          <button key={device.id} className={`device ${selected === device.id ? "active" : ""}`} onClick={() => setSelected(device.id)}>
            <span className="device-icon">⌁</span><span><strong>{device.name}</strong><small>{device.platform} · {device.is_online ? "Online" : "Offline"}</small></span>
          </button>
        )}
      </aside>
      <section className="content">
        <div className="stats">
          <div className="card stat"><span>Device</span><strong>{selectedDevice?.name || "—"}</strong><small>{selectedDevice?.device_identifier || "No selection"}</small></div>
          <div className="card stat"><span>Connection</span><strong>{selectedDevice ? (selectedDevice.is_online ? "Online" : "Offline") : "—"}</strong><small>{selectedDevice?.last_seen_at ? new Date(selectedDevice.last_seen_at).toLocaleString() : "No signal yet"}</small></div>
          <div className="card stat"><span>Battery</span><strong>{latest?.battery_level != null ? `${Math.round(latest.battery_level)}%` : "—"}</strong><small>Latest reported level</small></div>
          <div className="card stat"><span>Location updates</span><strong>{locations.length}</strong><small>Last 100 records</small></div>
        </div>
        <div className="card map-card">
          <div className="map-header"><div><h3>Live location</h3><p className="muted">Polling every 10 seconds while this dashboard is open.</p></div>{latest && <span className="live-pill">● LIVE</span>}</div>
          <MapPanel location={latest} />
        </div>
        <div className="card timeline">
          <div className="section-title"><span>Location timeline</span><span className="muted">{selectedDevice?.name || "Select a device"}</span></div>
          {locations.length === 0 ? <p className="muted empty">No location records received yet.</p> : locations.slice(0, 8).map(item =>
            <div className="timeline-row" key={item.id}><span className="timeline-dot" /><div><strong>{item.latitude.toFixed(5)}, {item.longitude.toFixed(5)}</strong><small>{new Date(item.recorded_at || item.received_at).toLocaleString()} · ±{item.accuracy_m ? Math.round(item.accuracy_m) : "—"}m</small></div></div>
          )}
        </div>
      </section>
    </section>
  </main>;
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("sentinel_token"));
  if (!token) return <Login onLogin={setToken} />;
  return <Dashboard token={token} onLogout={() => { localStorage.removeItem("sentinel_token"); setToken(null); }} />;
}

createRoot(document.getElementById("root")).render(<App />);
