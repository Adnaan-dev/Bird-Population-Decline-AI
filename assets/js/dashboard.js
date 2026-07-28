/* ============================================================
   Bird Population Decline AI — Dashboard logic
   ============================================================ */
"use strict";

const state = {
  mapboxToken: null,
  lat: null,
  lon: null,
  lastAnalysis: null,
  map: null,
  marker: null,
  chart: null,
};

/* ---------- helpers ---------- */
const $ = (sel) => document.querySelector(sel);

function toast(msg, type = "", action) {
  const t = $("#toast");
  t.innerHTML = "";
  const span = document.createElement("span");
  span.textContent = msg;
  t.appendChild(span);
  if (action && action.label && typeof action.fn === "function") {
    const btn = document.createElement("button");
    btn.className = "toast-action";
    btn.textContent = action.label;
    btn.addEventListener("click", () => {
      t.className = "toast " + type;
      action.fn();
    });
    t.appendChild(btn);
  }
  t.className = "toast show " + type;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.className = "toast " + type), action ? 8000 : 3800);
}

async function api(path, options) {
  const res = await fetch(path, options);
  const ct = res.headers.get("Content-Type") || "";
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    if (ct.includes("application/json")) {
      try { msg = (await res.json()).error || msg; } catch (_) {}
    }
    throw new Error(msg);
  }
  return ct.includes("application/json") ? res.json() : res;
}

/* ---------- login ---------- */
// Login removed — the dashboard is open to everyone.

/* ---------- tabs ---------- */
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("#tab-" + btn.dataset.tab).classList.add("active");
    if (state.map) setTimeout(() => state.map.resize(), 120);
  });
});

/* ---------- bootstrap (after login) ---------- */
async function bootstrap() {
  $("#year").textContent = new Date().getFullYear();
  // default date range: last 12 months
  const today = new Date();
  const past = new Date(); past.setFullYear(today.getFullYear() - 1);
  $("#endDate").value = today.toISOString().slice(0, 10);
  $("#startDate").value = past.toISOString().slice(0, 10);

  try {
    const cfg = await api("/api/config");
    state.mapboxToken = cfg.mapboxToken;
    if (!cfg.sentinelConfigured) {
      toast("Sentinel credentials not set on the server — analysis will fail.", "error");
    }
    initMap();
  } catch (err) {
    toast("Could not load configuration: " + err.message, "error");
  }
}

/* ---------- map ---------- */
function initMap() {
  if (!state.mapboxToken) {
    $("#map").innerHTML =
      '<div style="display:grid;place-items:center;height:100%;color:var(--text-dim);padding:2rem;text-align:center;">' +
      "Mapbox token not configured. Set MAPBOX_ACCESS_TOKEN in your environment.</div>";
    return;
  }
  mapboxgl.accessToken = state.mapboxToken;
  state.map = new mapboxgl.Map({
    container: "map",
    style: "mapbox://styles/mapbox/satellite-streets-v12",
    center: [78.0, 20.0],
    zoom: 3.2,
  });
  state.map.addControl(new mapboxgl.NavigationControl(), "top-right");
  state.map.on("click", (e) => {
    if (state.drawing) return; // ignore map clicks while drawing an area
    setLocation(e.lngLat.lat, e.lngLat.lng);
  });

  // Area analysis via Mapbox GL Draw (polygon -> bounding box).
  if (window.MapboxDraw) {
    state.draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: {},
    });
    state.map.addControl(state.draw);
    const onDraw = () => {
      const fc = state.draw.getAll();
      if (!fc.features.length) return;
      const coords = fc.features[fc.features.length - 1].geometry.coordinates[0];
      let w = 180, s = 90, e = -180, n = -90;
      coords.forEach(([lng, lat]) => {
        w = Math.min(w, lng); e = Math.max(e, lng);
        s = Math.min(s, lat); n = Math.max(n, lat);
      });
      state.bbox = [w, s, e, n];
      state.drawing = false;
      setLocation((s + n) / 2, (w + e) / 2, { keepBbox: true });
      $("#coordText").textContent =
        `Area ${w.toFixed(3)},${s.toFixed(3)} → ${e.toFixed(3)},${n.toFixed(3)}`;
      toast("Area selected — click Analyze to run it.", "success");
    };
    state.map.on("draw.create", onDraw);
    state.map.on("draw.update", onDraw);
  }

  // Deep link: /dashboard?lat=..&lon=..[&go=1] (used by the Explore page)
  state.map.on("load", () => {
    try {
      const p = new URLSearchParams(location.search);
      const lat = parseFloat(p.get("lat"));
      const lon = parseFloat(p.get("lon"));
      if (Number.isFinite(lat) && Number.isFinite(lon) &&
          lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        setLocation(lat, lon);
        state.map.flyTo({ center: [lon, lat], zoom: 12, essential: true });
        if (p.get("go") === "1") setTimeout(analyzeLocation, 400);
      }
    } catch (_) {}
  });
}

function setLocation(lat, lon, opts) {
  opts = opts || {};
  state.lat = lat;
  state.lon = lon;
  if (!opts.keepBbox) state.bbox = null;   // clicking/searching resets to point mode
  $("#coordText").textContent = `${lat.toFixed(5)}°, ${lon.toFixed(5)}°`;
  $("#analyzeBtn").disabled = false;
  const cp = $("#copyLinkBtn"); if (cp) cp.disabled = false;
  const sv = $("#saveLocBtn"); if (sv) sv.disabled = false;

  if (state.marker) state.marker.remove();
  state.marker = new mapboxgl.Marker({ color: "#10b981" })
    .setLngLat([lon, lat])
    .addTo(state.map);

  // enable time-series controls
  $("#seriesNoLoc").classList.add("hidden");
  $("#seriesControls").classList.remove("hidden");
  $("#seriesCoord").textContent = `${lat.toFixed(5)}°, ${lon.toFixed(5)}°`;

  // enable change-detection controls
  $("#changeNoLoc").classList.add("hidden");
  $("#changeControls").classList.remove("hidden");
  $("#changeCoord").textContent = `${lat.toFixed(5)}°, ${lon.toFixed(5)}°`;
  if (!$("#date2").value) {
    const today = new Date();
    const yearAgo = new Date(); yearAgo.setFullYear(today.getFullYear() - 1);
    $("#date2").value = today.toISOString().slice(0, 10);
    $("#date1").value = yearAgo.toISOString().slice(0, 10);
  }
}

/* ---------- analyze ---------- */
$("#analyzeBtn").addEventListener("click", analyzeLocation);

async function analyzeLocation() {
  if (state.lat == null) return;
  $("#results").classList.add("hidden");
  $("#analyzeLoading").classList.remove("hidden");
  $("#analyzeBtn").disabled = true;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90000); // 90s safety timeout
  try {
    const data = await api("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat: state.lat, lon: state.lon, bbox: state.bbox }),
      signal: controller.signal,
    });
    state.lastAnalysis = data;
    renderResults(data);
    $("#results").classList.remove("hidden");
    $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    let msg = err.message;
    if (err.name === "AbortError") {
      msg = "Analysis timed out. The satellite service was slow — please try again.";
    } else if (/failed to fetch|networkerror/i.test(msg)) {
      msg = "Could not reach the server. Check that the app is running, then retry.";
    }
    toast("Analysis failed: " + msg, "error", { label: "Retry", fn: analyzeLocation });
  } finally {
    clearTimeout(timer);
    $("#analyzeLoading").classList.add("hidden");
    $("#analyzeBtn").disabled = false;
  }
}

function metric(label, value, note) {
  return `<div class="metric"><div class="mlabel">${label}</div>
    <div class="mvalue gradient-text">${value}</div>
    ${note ? `<div class="mnote">${note}</div>` : ""}</div>`;
}

/* ---------- gauges ---------- */
function scoreColor(v, invert) {
  // invert=false: high is good (green). invert=true: high is bad (red).
  const good = "#10b981", mid = "#f59e0b", bad = "#ef4444";
  if (!invert) return v > 60 ? good : v > 30 ? mid : bad;
  return v > 60 ? bad : v > 30 ? mid : good;
}

function animateGauge(gaugeId, valId, target, color, reduceMotion) {
  const gauge = document.getElementById(gaugeId);
  const valEl = document.getElementById(valId);
  if (!gauge || !valEl) return;
  gauge.style.setProperty("--gcolor", color);
  if (reduceMotion) {
    gauge.style.setProperty("--pct", target);
    valEl.textContent = target.toFixed(1);
    return;
  }
  const dur = 900, start = performance.now();
  function frame(now) {
    const t = Math.min((now - start) / dur, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    const cur = target * eased;
    gauge.style.setProperty("--pct", cur.toFixed(1));
    valEl.textContent = cur.toFixed(1);
    if (t < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function renderGauges(habitat, risk, habitatStatus, riskStatus) {
  const reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  animateGauge("habitatGauge", "habitatGaugeVal", habitat, scoreColor(habitat, false), reduceMotion);
  animateGauge("riskGauge", "riskGaugeVal", risk, scoreColor(risk, true), reduceMotion);
  const summary = $("#scoreSummary");
  if (summary) {
    summary.innerHTML =
      `Habitat health is <b style="color:var(--text);">${habitatStatus}</b> ` +
      `(${habitat.toFixed(1)}/100). Bird-population-decline risk is ` +
      `<b style="color:var(--text);">${riskStatus}</b> (${risk.toFixed(1)}/100). ` +
      `Risk is derived as <code>100 − habitat</code>, so the two always sum to 100.`;
  }
}

function renderResults(d) {
  const habitatStatus = d.habitat > 60 ? "✅ Healthy" : d.habitat > 30 ? "⚠️ Moderate" : "❌ Critical";
  const riskStatus = d.risk > 60 ? "🔴 High" : d.risk > 30 ? "🟡 Medium" : "🟢 Low";
  const ndviStatus = d.ndvi_mean > 0.5 ? "🟢 Excellent" : d.ndvi_mean > 0.2 ? "🟡 Good" : "🔴 Poor";

  renderGauges(d.habitat, d.risk, habitatStatus, riskStatus);

  $("#metricsRow").innerHTML =
    metric("🌿 Habitat Health", d.habitat.toFixed(1), habitatStatus) +
    metric("🦅 Bird Decline Risk", d.risk.toFixed(1), riskStatus) +
    metric("📈 Mean NDVI", d.ndvi_mean.toFixed(3), ndviStatus + " vegetation") +
    metric("💧 Mean NDWI", d.ndwi_mean.toFixed(3), "water index") +
    metric("🏙️ Mean NDBI", d.ndbi_mean.toFixed(3), "built-up index") +
    (d.indices ? (
      metric("🌱 EVI", d.indices.evi.toFixed(3), "enhanced vegetation") +
      metric("💦 NDMI", d.indices.ndmi.toFixed(3), "moisture") +
      metric("🔥 NBR", d.indices.nbr.toFixed(3), "burn / veg")
    ) : "");

  const imgs = d.images;
  const tile = (src, name, sub) =>
    `<div class="img-tile"><img src="${src}" alt="${name}" loading="lazy" />
      <div class="caption">${name}<small>${sub}</small></div></div>`;
  $("#imgGrid").innerHTML =
    tile(imgs.rgb, "RGB", "true color") +
    tile(imgs.ndvi, "NDVI", "vegetation") +
    tile(imgs.ndwi, "NDWI", "water") +
    tile(imgs.ndbi, "NDBI", "built-up") +
    (imgs.evi ? tile(imgs.evi, "EVI", "enhanced veg") : "") +
    (imgs.ndmi ? tile(imgs.ndmi, "NDMI", "moisture") : "") +
    (imgs.nbr ? tile(imgs.nbr, "NBR", "burn / veg") : "");

  $("#landcoverBadge").textContent = "🌍 " + d.landcover;

  // Show resolved place name (reverse-geocoded) alongside the coordinates.
  if (d.place) {
    $("#coordText").textContent = `${d.place}  (${d.lat.toFixed(5)}°, ${d.lon.toFixed(5)}°)`;
  }

  renderScene(d.scene);
  renderWeather(d.weather);
  renderBirds(d.birds);
}

function renderWeather(weather) {
  const card = $("#weatherCard");
  if (!weather || !weather.main) { card.classList.add("hidden"); return; }
  const m = weather.main;
  const w = (weather.weather && weather.weather[0]) || {};
  const wind = weather.wind && weather.wind.speed != null ? weather.wind.speed : "N/A";
  const clouds = weather.clouds && weather.clouds.all != null ? weather.clouds.all : "N/A";
  const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");

  $("#weatherRow").innerHTML =
    metric("🌡️ Temperature", `${m.temp}°C`, `Feels like ${m.feels_like ?? "N/A"}°C`) +
    metric("💧 Humidity", `${m.humidity}%`, `Pressure ${m.pressure ?? "N/A"} hPa`) +
    metric("⛅ Conditions", cap(w.main || "—"), cap(w.description || "")) +
    metric("💨 Wind", `${wind} m/s`, `Clouds ${clouds}%`);
  card.classList.remove("hidden");
}

/* ---------- PDF report ---------- */
$("#reportBtn").addEventListener("click", async () => {
  const d = state.lastAnalysis;
  if (!d) return;
  const btn = $("#reportBtn");
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "⏳ Generating…";
  try {
    const res = await api("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lat: d.lat, lon: d.lon, habitat: d.habitat, risk: d.risk,
        ndvi_mean: d.ndvi_mean, landcover: d.landcover, weather: d.weather,
        place: d.place,
      }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `habitat_report_${d.lat.toFixed(3)}_${d.lon.toFixed(3)}.pdf`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    toast("PDF report downloaded.", "success");
  } catch (err) {
    toast("Report failed: " + err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
});

/* ---------- time series ---------- */
$("#seriesBtn").addEventListener("click", async () => {
  if (state.lat == null) return;
  const start = $("#startDate").value;
  const end = $("#endDate").value;
  if (!start || !end) return toast("Pick a start and end date.", "error");
  if (start > end) return toast("Start date must be before end date.", "error");

  $("#seriesChartCard").classList.add("hidden");
  $("#seriesLoading").classList.remove("hidden");
  const btn = $("#seriesBtn");
  btn.disabled = true;

  try {
    const data = await api("/api/timeseries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat: state.lat, lon: state.lon, start, end }),
    });
    if (!data.dates.length) {
      toast("No usable imagery in that range (clouds/missing). Try a wider range.", "error");
      return;
    }
    renderChart(data.dates, data.values, data.stats);
    renderSeriesStats(data.stats);
    $("#seriesChartCard").classList.remove("hidden");
    $("#seriesChartCard").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    toast("Time-series failed: " + err.message, "error");
  } finally {
    $("#seriesLoading").classList.add("hidden");
    btn.disabled = false;
  }
});

function renderChart(labels, values, stats) {
  const ctx = $("#ndviChart").getContext("2d");
  if (state.chart) state.chart.destroy();
  const grad = ctx.createLinearGradient(0, 0, 0, 300);
  grad.addColorStop(0, "rgba(16,185,129,0.35)");
  grad.addColorStop(1, "rgba(16,185,129,0.02)");

  const datasets = [];
  // Seasonal baseline band (mean ± 1 std) drawn behind the trend line.
  if (stats && stats.baseline_low != null && stats.baseline_high != null) {
    const low = labels.map(() => stats.baseline_low);
    const high = labels.map(() => stats.baseline_high);
    const mean = labels.map(() => stats.mean);
    datasets.push({
      label: "baseline low", data: low, borderColor: "rgba(0,0,0,0)",
      pointRadius: 0, fill: false, tension: 0,
    });
    datasets.push({
      label: "typical range (±1σ)", data: high, borderColor: "rgba(0,0,0,0)",
      backgroundColor: "rgba(6,182,212,0.12)", pointRadius: 0, fill: "-1", tension: 0,
    });
    datasets.push({
      label: "seasonal mean", data: mean, borderColor: "rgba(148,163,184,0.9)",
      borderDash: [6, 5], borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0,
    });
  }
  datasets.push({
    label: "Mean NDVI", data: values, borderColor: "#10b981",
    backgroundColor: grad, borderWidth: 2.5, pointRadius: 4,
    pointBackgroundColor: "#4ade80", tension: 0.3, fill: true,
  });

  state.chart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e8eef7", filter: (i) => i.text !== "baseline low" } } },
      scales: {
        x: { ticks: { color: "#9fb0c8" }, grid: { color: "rgba(255,255,255,0.06)" } },
        y: {
          min: -1, max: 1,
          ticks: { color: "#9fb0c8" },
          grid: { color: "rgba(255,255,255,0.06)" },
          title: { display: true, text: "Mean NDVI", color: "#9fb0c8" },
        },
      },
    },
  });
}

function renderSeriesStats(stats) {
  const el = $("#seriesStats");
  if (!el) return;
  if (!stats || stats.mean == null) { el.classList.add("hidden"); return; }
  const anomaly = stats.anomaly;
  const dir = anomaly > 0.02 ? "above" : anomaly < -0.02 ? "below" : "in line with";
  const tone = anomaly < -0.05 ? "⚠️" : "✅";
  el.innerHTML =
    `${tone} Latest NDVI <b>${stats.latest}</b> is <b>${dir}</b> the period mean ` +
    `<b>${stats.mean}</b> (anomaly ${anomaly >= 0 ? "+" : ""}${anomaly}). ` +
    `Typical range ${stats.baseline_low} – ${stats.baseline_high} (±1σ); ` +
    `observed min ${stats.min}, max ${stats.max}.`;
  el.classList.remove("hidden");
}

/* ---------- scene metadata & birds ---------- */
function renderScene(scene) {
  const card = $("#sceneCard");
  if (!scene || !scene.date) { card.classList.add("hidden"); return; }
  const cc = scene.cloud_cover == null ? "N/A" : scene.cloud_cover + "%";
  $("#sceneRow").innerHTML =
    metric("📅 Acquired", scene.date, "most recent low-cloud scene") +
    metric("☁️ Cloud cover", cc, "of source tile");
  card.classList.remove("hidden");
}

function renderBirds(birds) {
  const card = $("#birdsCard");
  if (!birds) { card.classList.add("hidden"); return; }
  $("#birdsRow").innerHTML =
    metric("🐦 Occurrences", (birds.count || 0).toLocaleString(), `within ${birds.radius_km} km`) +
    metric("🎼 Species richness", birds.species_richness || 0, `from ${birds.sampled} sampled`);
  const esc = (s) => String(s).replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));
  const chips = (birds.top_species || [])
    .map((s) => `<span class="chip"><i>${esc(s.name)}</i> <b>${s.count}</b></span>`).join("");
  $("#birdsSpecies").innerHTML = chips ? `<div class="chip-label">Most recorded species:</div>${chips}` : "";
  card.classList.remove("hidden");
}

/* ---------- place search (Mapbox forward geocoding) ---------- */
$("#searchForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("#searchInput").value.trim();
  if (!q) return;
  if (!state.mapboxToken) return toast("Map is still loading — try again in a moment.", "error");
  try {
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(q)}.json` +
      `?access_token=${state.mapboxToken}&limit=1`;
    const res = await fetch(url);
    const data = await res.json();
    const f = (data.features || [])[0];
    if (!f) return toast("No match found for that place.", "error");
    const [lon, lat] = f.center;
    setLocation(lat, lon);
    state.map.flyTo({ center: [lon, lat], zoom: 11, essential: true });
    toast(`Found: ${f.place_name}`, "success");
  } catch (err) {
    toast("Search failed: " + err.message, "error");
  }
});

/* ---------- copy shareable link ---------- */
$("#copyLinkBtn")?.addEventListener("click", async () => {
  if (state.lat == null) return;
  const url = `${location.origin}/dashboard?lat=${state.lat.toFixed(5)}&lon=${state.lon.toFixed(5)}&go=1`;
  try {
    await navigator.clipboard.writeText(url);
    toast("Shareable link copied to clipboard.", "success");
  } catch (_) {
    window.prompt("Copy this link:", url);
  }
});

/* ---------- saved / recent locations ---------- */
function loadSaved() {
  try { return JSON.parse(localStorage.getItem("bpd_saved") || "[]"); } catch (_) { return []; }
}
function storeSaved(arr) {
  try { localStorage.setItem("bpd_saved", JSON.stringify(arr.slice(0, 12))); } catch (_) {}
}
function renderSavedChips() {
  const arr = loadSaved();
  const wrap = $("#savedWrap"), box = $("#savedChips");
  if (!wrap || !box) return;
  if (!arr.length) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  box.innerHTML = arr.map((l, i) =>
    `<span class="loc-chip" data-i="${i}" tabindex="0" role="button">📍 ${l.name} <span class="x" data-del="${i}" title="Remove">×</span></span>`
  ).join("");
  box.querySelectorAll(".loc-chip").forEach((chip) => {
    chip.addEventListener("click", (e) => {
      if (e.target.dataset.del != null) {
        e.stopPropagation();
        const a = loadSaved(); a.splice(+e.target.dataset.del, 1); storeSaved(a); renderSavedChips();
        return;
      }
      const l = loadSaved()[+chip.dataset.i];
      if (!l) return;
      setLocation(l.lat, l.lon);
      state.map.flyTo({ center: [l.lon, l.lat], zoom: 11, essential: true });
    });
  });
}
$("#saveLocBtn")?.addEventListener("click", () => {
  if (state.lat == null) return;
  const arr = loadSaved();
  const name = (state.lastAnalysis && state.lastAnalysis.place)
    ? state.lastAnalysis.place.split(",")[0]
    : `${state.lat.toFixed(3)}, ${state.lon.toFixed(3)}`;
  // de-dup by rounded coords
  const key = `${state.lat.toFixed(3)},${state.lon.toFixed(3)}`;
  const filtered = arr.filter((l) => `${l.lat.toFixed(3)},${l.lon.toFixed(3)}` !== key);
  filtered.unshift({ name, lat: state.lat, lon: state.lon });
  storeSaved(filtered); renderSavedChips();
  toast("Location saved.", "success");
});

/* ---------- draw area ---------- */
$("#drawAreaBtn")?.addEventListener("click", () => {
  if (!state.draw) return toast("Area drawing is unavailable.", "error");
  state.draw.deleteAll();
  state.draw.changeMode("draw_polygon");
  state.drawing = true;
  toast("Draw a polygon on the map — double-click to finish.", "success");
});

/* ---------- CSV / GeoJSON export ---------- */
function download(filename, text, mime) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}
$("#csvBtn")?.addEventListener("click", () => {
  const d = state.lastAnalysis;
  if (!d) return;
  const ix = d.indices || {};
  const rows = [
    ["field", "value"],
    ["place", d.place || ""], ["lat", d.lat], ["lon", d.lon],
    ["habitat", d.habitat.toFixed(2)], ["risk", d.risk.toFixed(2)],
    ["ndvi_mean", d.ndvi_mean], ["ndwi_mean", d.ndwi_mean], ["ndbi_mean", d.ndbi_mean],
    ["evi", ix.evi], ["savi", ix.savi], ["ndmi", ix.ndmi], ["nbr", ix.nbr],
    ["landcover", d.landcover],
    ["scene_date", d.scene && d.scene.date], ["scene_cloud_cover", d.scene && d.scene.cloud_cover],
    ["bird_occurrences", d.birds && d.birds.count], ["species_richness", d.birds && d.birds.species_richness],
  ];
  const csv = rows.map((r) => r.map((v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`).join(",")).join("\n");
  download(`habitat_${d.lat.toFixed(3)}_${d.lon.toFixed(3)}.csv`, csv, "text/csv");
  toast("CSV exported.", "success");
});
$("#geojsonBtn")?.addEventListener("click", () => {
  const d = state.lastAnalysis;
  if (!d) return;
  const gj = {
    type: "Feature",
    geometry: { type: "Point", coordinates: [d.lon, d.lat] },
    properties: {
      place: d.place, habitat: d.habitat, risk: d.risk,
      ndvi_mean: d.ndvi_mean, ndwi_mean: d.ndwi_mean, ndbi_mean: d.ndbi_mean,
      indices: d.indices, landcover: d.landcover, scene: d.scene,
      birds: d.birds ? { count: d.birds.count, species_richness: d.birds.species_richness } : null,
    },
  };
  download(`habitat_${d.lat.toFixed(3)}_${d.lon.toFixed(3)}.geojson`,
    JSON.stringify(gj, null, 2), "application/geo+json");
  toast("GeoJSON exported.", "success");
});

/* ---------- change detection ---------- */
$("#changeBtn")?.addEventListener("click", runChange);
async function runChange() {
  if (state.lat == null) return;
  const d1 = $("#date1").value, d2 = $("#date2").value;
  if (!d1 || !d2) return toast("Pick both dates.", "error");
  if (d1 === d2) return toast("Pick two different dates.", "error");
  $("#changeResults").classList.add("hidden");
  $("#changeLoading").classList.remove("hidden");
  const btn = $("#changeBtn"); btn.disabled = true;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const data = await api("/api/change", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat: state.lat, lon: state.lon, date1: d1, date2: d2 }),
      signal: controller.signal,
    });
    renderChange(data);
    $("#changeResults").classList.remove("hidden");
    $("#changeResults").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    const msg = err.name === "AbortError" ? "Timed out — try again." : err.message;
    toast("Change detection failed: " + msg, "error", { label: "Retry", fn: runChange });
  } finally {
    clearTimeout(timer);
    $("#changeLoading").classList.add("hidden");
    btn.disabled = false;
  }
}
function renderChange(d) {
  const arrow = d.ndvi_delta > 0 ? "▲" : d.ndvi_delta < 0 ? "▼" : "▬";
  $("#changeMetrics").innerHTML =
    metric("📅 Dates", `${d.date1} → ${d.date2}`, "compared scenes") +
    metric("Δ Mean NDVI", `${arrow} ${d.ndvi_delta.toFixed(3)}`, `${d.ndvi_mean_1} → ${d.ndvi_mean_2}`) +
    metric("🟥 Vegetation loss", d.pct_vegetation_loss + "%", "area NDVI dropped > 0.1") +
    metric("🟦 Vegetation gain", d.pct_vegetation_gain + "%", "area NDVI rose > 0.1");
  const tile = (src, name, sub) =>
    `<div class="img-tile"><img src="${src}" alt="${name}" loading="lazy" />
      <div class="caption">${name}<small>${sub}</small></div></div>`;
  $("#changeImgs").innerHTML =
    tile(d.images.ndvi1, "NDVI " + d.date1, "earlier") +
    tile(d.images.ndvi2, "NDVI " + d.date2, "later") +
    tile(d.images.diff, "Δ NDVI", "blue = gain, red = loss");
}

renderSavedChips();

/* ---------- go ---------- */
bootstrap();
