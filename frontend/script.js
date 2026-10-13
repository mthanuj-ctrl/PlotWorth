const BACKEND_BASE = "https://plotworth-api.onrender.com";
const TIER_COLORS = { "Budget": "#2e7d32", "Mid-Tier": "#e65100", "Luxury": "#b71c1c" };
const state = { data: null, compareData: null, compareMode: false, map: null, clusterGroup: null };
const $ = (id) => document.getElementById(id);
function showFeedback(msg) { $("feedback").textContent = msg || ""; }
function startLoading() { const bar = $("loading-bar"); bar.style.width = "0%"; requestAnimationFrame(() => { bar.style.width = "70%"; }); }
function stopLoading() { const bar = $("loading-bar"); bar.style.width = "100%"; setTimeout(() => { bar.style.width = "0%"; }, 400); }
function formatINR(n) { if (n === null || n === undefined || isNaN(n)) return "\u2014"; return "Rs " + Math.round(n).toLocaleString("en-IN"); }
function formatINRpsf(n) { if (n === null || n === undefined || isNaN(n)) return "\u2014"; return "Rs " + Math.round(n).toLocaleString("en-IN") + " / sqft"; }
function safeNum(n) { return (n === null || n === undefined || isNaN(n)) ? 0 : Number(n); }
async function fetchLocality(query) {
  const url = BACKEND_BASE + "/api/locality/search?q=" + encodeURIComponent(query);
  const r = await fetch(url);
  if (!r.ok) throw new Error("Backend returned " + r.status);
  return r.json();
}
async function fetchReverse(lat, lng) {
  const url = BACKEND_BASE + "/api/locality/reverse?lat=" + lat + "&lng=" + lng;
  const r = await fetch(url);
  if (!r.ok) throw new Error("Reverse geocode failed");
  return r.json();
}
function renderMetrics(d) {
  $("m-locality").textContent = d.canonical || d.query || "\u2014";
  $("m-city").textContent = d.city || "\u2014";
  $("m-ppsf").textContent = formatINRpsf(d.price_per_sqft);
  $("m-bhk").textContent = d.median_bhk || "\u2014";
  $("m-buildings").textContent = d.building_count || 0;
  $("m-land").textContent = d.land_count || 0;
  $("m-listings").textContent = d.listings_count || 0;
  const yoy = (d.historical && d.historical.yoy_change_pct) || (d.market && d.market.yoy_change_pct) || 0;
  $("m-yoy").textContent = (yoy >= 0 ? "+" : "") + Number(yoy).toFixed(2) + " %";
  const years = (d.historical && d.historical.years) || [];
  const prices = (d.historical && d.historical.prices) || [];
  Plotly.newPlot("chart-historical", [{ x: years.map(String), y: prices, type: "bar", marker: { color: "#e65100", line: { color: "#2c2c2c", width: 1.5 } }, hovertemplate: "%{x}<br>Rs %{y:,.0f} / sqft<extra></extra>" }], { margin: { l: 60, r: 10, t: 20, b: 40 }, paper_bgcolor: "#f4f1ec", plot_bgcolor: "#f4f1ec", font: { family: "Segoe UI, Helvetica Neue, sans-serif", color: "#2c2c2c" }, xaxis: { title: "Year", linecolor: "#2c2c2c", mirror: true }, yaxis: { title: "Rs / sqft", linecolor: "#2c2c2c", mirror: true }, bargap: 0.4 }, { responsive: true, displayModeBar: false });
}
function renderForecast(d) {
  const f = d.forecast || {};
  $("f-m6").textContent = formatINRpsf(f.m6);
  $("f-y2").textContent = formatINRpsf(f.y2);
  $("f-y5").textContent = formatINRpsf(f.y5);
  const years = ((d.historical && d.historical.years) || []).map(Number);
  const prices = (d.historical && d.historical.prices) || [];
  const now = new Date().getFullYear();
  const fYears = [now + 0.5, now + 2, now + 5];
  const fVals = [f.m6, f.y2, f.y5];
  const allX = years.concat(fYears);
  const foreY = years.map(function() { return null; }).slice(0, -1).concat([prices[prices.length - 1] || null], fVals);
  Plotly.newPlot("chart-forecast", [
    { x: years.map(String), y: prices, type: "scatter", mode: "lines+markers", name: "Historical", line: { color: "#2c2c2c", width: 2 }, marker: { color: "#2c2c2c", size: 8 }, hovertemplate: "%{x}<br>Rs %{y:,.0f} / sqft<extra></extra>" },
    { x: allX.map(String), y: foreY, type: "scatter", mode: "lines+markers", name: "Forecast", line: { color: "#e65100", width: 2, dash: "dash" }, marker: { color: "#e65100", size: 9 }, hovertemplate: "%{x}<br>Rs %{y:,.0f} / sqft<extra></extra>" }
  ], { margin: { l: 60, r: 10, t: 20, b: 40 }, paper_bgcolor: "#f4f1ec", plot_bgcolor: "#f4f1ec", font: { family: "Segoe UI, Helvetica Neue, sans-serif", color: "#2c2c2c" }, xaxis: { title: "Year", linecolor: "#2c2c2c", mirror: true }, yaxis: { title: "Rs / sqft", linecolor: "#2c2c2c", mirror: true }, showlegend: true, legend: { orientation: "h", y: 1.15 } }, { responsive: true, displayModeBar: false });
}
function renderEval(d) {
  const e = d.evaluation || {};
  $("e-r2").textContent = Number(e.r2 || 0).toFixed(4);
  $("e-rmse").textContent = formatINR(e.rmse);
  $("e-mae").textContent = formatINR(e.mae);
  $("e-mape").textContent = Number(e.mape || 0).toFixed(2) + " %";
}
function renderTiers(d) {
  const dist = d.tier_distribution || { Budget: 0, "Mid-Tier": 0, Luxury: 0 };
  const labels = ["Budget", "Mid-Tier", "Luxury"];
  const values = labels.map(function(l) { return safeNum(dist[l]); });
  const colors = labels.map(function(l) { return TIER_COLORS[l]; });
  Plotly.newPlot("chart-tiers", [{ labels: labels, values: values, type: "pie", hole: 0.55, marker: { colors: colors, line: { color: "#2c2c2c", width: 2 } }, textinfo: "label+value", hovertemplate: "%{label}: %{value} properties<extra></extra>" }], { margin: { l: 10, r: 10, t: 20, b: 20 }, paper_bgcolor: "#f4f1ec", font: { family: "Segoe UI, Helvetica Neue, sans-serif", color: "#2c2c2c" }, showlegend: true, legend: { orientation: "h", y: -0.05 } }, { responsive: true, displayModeBar: false });
}
function renderStats(d) {
  const comps = d.comparables || [];
  if (comps.length) {
    Plotly.newPlot("chart-compare", [{ x: comps.map(function(c) { return c.locality; }), y: comps.map(function(c) { return c.price_per_sqft; }), type: "bar", marker: { color: "#2e7d32", line: { color: "#2c2c2c", width: 1.5 } }, customdata: comps.map(function(c) { return [c.distance_km, c.forecast_5y]; }), hovertemplate: "%{x}<br>Rs %{y:,.0f} / sqft<br>Distance %{customdata[0]} km<br>5Y forecast Rs %{customdata[1]:,.0f}<extra></extra>" }], { margin: { l: 60, r: 10, t: 20, b: 60 }, paper_bgcolor: "#f4f1ec", plot_bgcolor: "#f4f1ec", font: { family: "Segoe UI, Helvetica Neue, sans-serif", color: "#2c2c2c" }, xaxis: { linecolor: "#2c2c2c", mirror: true, tickangle: -30 }, yaxis: { title: "Rs / sqft", linecolor: "#2c2c2c", mirror: true } }, { responsive: true, displayModeBar: false });
  }
  const props = d.properties || [];
  if (props.length) {
    Plotly.newPlot("chart-hist", [{ x: props.map(function(p) { return p.price_per_sqft; }), type: "histogram", marker: { color: "#e65100", line: { color: "#2c2c2c", width: 1.5 } }, nbinsx: 18, hovertemplate: "Rs %{x:,.0f} / sqft<br>%{y} properties<extra></extra>" }], { margin: { l: 55, r: 10, t: 20, b: 45 }, paper_bgcolor: "#f4f1ec", plot_bgcolor: "#f4f1ec", font: { family: "Segoe UI, Helvetica Neue, sans-serif", color: "#2c2c2c" }, xaxis: { title: "Rs / sqft", linecolor: "#2c2c2c", mirror: true }, yaxis: { title: "Count", linecolor: "#2c2c2c", mirror: true } }, { responsive: true, displayModeBar: false });
    Plotly.newPlot("chart-scatter", [{ x: props.map(function(p) { return p.area_sqft; }), y: props.map(function(p) { return p.price_per_sqft; }), text: props.map(function(p) { return p.address; }), mode: "markers", type: "scatter", marker: { size: 10, color: props.map(function(p) { return TIER_COLORS[p.tier] || "#2c2c2c"; }), line: { color: "#2c2c2c", width: 1.5 } }, hovertemplate: "%{text}<br>%{x} sqft<br>Rs %{y:,.0f} / sqft<extra></extra>" }], { margin: { l: 60, r: 10, t: 20, b: 45 }, paper_bgcolor: "#f4f1ec", plot_bgcolor: "#f4f1ec", font: { family: "Segoe UI, Helvetica Neue, sans-serif", color: "#2c2c2c" }, xaxis: { title: "Area (sqft)", linecolor: "#2c2c2c", mirror: true }, yaxis: { title: "Rs / sqft", linecolor: "#2c2c2c", mirror: true } }, { responsive: true, displayModeBar: false });
  }
}
function renderAmenities(d) {
  const a = d.amenities || {};
  const cityAvg = { metro_distance_km: 4.5, school_count: 22, hospital_count: 8, park_count: 12 };
  function norm(v, max) { return Math.min(1, safeNum(v) / max); }
  const cats = ["Metro distance", "Schools", "Hospitals", "Parks"];
  const locVals = [1 - norm(a.metro_distance_km, 15), norm(a.school_count, 40), norm(a.hospital_count, 20), norm(a.park_count, 25)];
  const cityVals = [1 - norm(cityAvg.metro_distance_km, 15), norm(cityAvg.school_count, 40), norm(cityAvg.hospital_count, 20), norm(cityAvg.park_count, 25)];
  Plotly.newPlot("chart-radar", [
    { type: "scatterpolar", r: locVals.concat(locVals[0]), theta: cats.concat(cats[0]), fill: "toself", name: d.canonical || "Locality", line: { color: "#e65100", width: 2 }, fillcolor: "rgba(230,81,0,0.22)" },
    { type: "scatterpolar", r: cityVals.concat(cityVals[0]), theta: cats.concat(cats[0]), fill: "toself", name: "City average", line: { color: "#2c2c2c", width: 2, dash: "dot" }, fillcolor: "rgba(44,44,44,0.08)" }
  ], { margin: { l: 40, r: 40, t: 30, b: 30 }, paper_bgcolor: "#f4f1ec", font: { family: "Segoe UI, Helvetica Neue, sans-serif", color: "#2c2c2c" }, polar: { bgcolor: "#f4f1ec", radialaxis: { visible: true, range: [0, 1], linecolor: "#2c2c2c", gridcolor: "#c9c2b5" }, angularaxis: { linecolor: "#2c2c2c", gridcolor: "#c9c2b5" } }, showlegend: true, legend: { orientation: "h", y: -0.1 } }, { responsive: true, displayModeBar: false });
}
function renderHeatmap(d) {
  const comps = (d.comparables || []).slice(0, 5);
  const years = ((d.historical && d.historical.years) || []).slice(-4);
  if (!comps.length || !years.length) return;
  const z = comps.map(function(c, idx) { return years.map(function(_, j) { const seed = (idx + 1) * (j + 2); return Number((4 + ((seed * 7) % 90) / 10).toFixed(2)); }); });
  Plotly.newPlot("chart-heatmap", [{ z: z, x: years.map(String), y: comps.map(function(c) { return c.locality; }), type: "heatmap", colorscale: [[0, "#faf8f5"], [0.5, "#e65100"], [1, "#b71c1c"]], hovertemplate: "%{y}<br>%{x}: %{z:.2f} %<extra></extra>" }], { margin: { l: 100, r: 10, t: 20, b: 40 }, paper_bgcolor: "#f4f1ec", plot_bgcolor: "#f4f1ec", font: { family: "Segoe UI, Helvetica Neue, sans-serif", color: "#2c2c2c" } }, { responsive: true, displayModeBar: false });
}
function renderRecommendations(d) {
  const list = $("rec-list");
  list.innerHTML = "";
  const recs = d.recommendations || [];
  if (!recs.length) { const li = document.createElement("li"); li.textContent = "No alternative localities found nearby."; list.appendChild(li); return; }
  recs.forEach(function(r) {
    const li = document.createElement("li");
    li.innerHTML = '<span class="rec-name">' + r.locality + '</span> &mdash; ' + formatINRpsf(r.price_per_sqft) + ' | 5Y forecast ' + formatINRpsf(r.forecast_5y) + ' | ' + Number(r.distance_km).toFixed(2) + ' km<br><span class="reason">' + r.reason + '</span>';
    list.appendChild(li);
  });
}
function renderMap(d) {
  if (!state.map) {
    state.map = L.map("map", { zoomControl: true }).setView([12.9716, 77.5946], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(state.map);
    state.clusterGroup = L.markerClusterGroup();
    state.map.addLayer(state.clusterGroup);
  }
  state.clusterGroup.clearLayers();
  const center = [d.lat, d.lng];
  state.map.setView(center, 12);
  L.circleMarker(center, { radius: 8, color: "#2c2c2c", weight: 2, fillColor: "#2c2c2c", fillOpacity: 1 }).bindPopup("<strong>" + (d.canonical || d.query) + "</strong><br>Search center").addTo(state.clusterGroup);
  (d.properties || []).forEach(function(p) {
    const color = TIER_COLORS[p.tier] || "#2c2c2c";
    let marker;
    if (p.type === "Land") {
      const icon = L.divIcon({ className: "", html: '<div style="width:12px;height:12px;background:' + color + ';border:2px solid #2c2c2c;"></div>', iconSize: [16, 16], iconAnchor: [8, 8] });
      marker = L.marker([p.lat, p.lng], { icon: icon });
    } else {
      marker = L.circleMarker([p.lat, p.lng], { radius: 6, color: "#2c2c2c", weight: 1.5, fillColor: color, fillOpacity: 1 });
    }
    marker.bindPopup("<strong>" + (p.address || "Property") + "</strong><br>Type: " + p.type + "<br>Tier: " + p.tier + "<br>BHK: " + (p.bhk || "\u2014") + "<br>Area: " + (p.area_sqft || "\u2014") + " sqft<br>Rate: " + formatINRpsf(p.price_per_sqft));
    state.clusterGroup.addLayer(marker);
  });
  setTimeout(function() { state.map.invalidateSize(); }, 150);
}
function renderAll(d) { renderMetrics(d); renderForecast(d); renderEval(d); renderTiers(d); renderStats(d); renderAmenities(d); renderHeatmap(d); renderRecommendations(d); renderMap(d); }
function renderCompare() {
  if (!state.compareMode || !state.data || !state.compareData) return;
  const a = state.data, b = state.compareData;
  const container = document.createElement("div");
  container.innerHTML = "<h3>Side-by-side comparison</h3><table class='metrics-table'><tbody><tr><td>Locality</td><td>" + (a.canonical || a.query) + "</td><td>" + (b.canonical || b.query) + "</td></tr><tr><td>City</td><td>" + (a.city || "\u2014") + "</td><td>" + (b.city || "\u2014") + "</td></tr><tr><td>Price per sqft</td><td>" + formatINRpsf(a.price_per_sqft) + "</td><td>" + formatINRpsf(b.price_per_sqft) + "</td></tr><tr><td>6M forecast</td><td>" + formatINRpsf(a.forecast && a.forecast.m6) + "</td><td>" + formatINRpsf(b.forecast && b.forecast.m6) + "</td></tr><tr><td>2Y forecast</td><td>" + formatINRpsf(a.forecast && a.forecast.y2) + "</td><td>" + formatINRpsf(b.forecast && b.forecast.y2) + "</td></tr><tr><td>5Y forecast</td><td>" + formatINRpsf(a.forecast && a.forecast.y5) + "</td><td>" + formatINRpsf(b.forecast && b.forecast.y5) + "</td></tr><tr><td>R squared</td><td>" + Number((a.evaluation && a.evaluation.r2) || 0).toFixed(4) + "</td><td>" + Number((b.evaluation && b.evaluation.r2) || 0).toFixed(4) + "</td></tr><tr><td>Budget</td><td>" + ((a.tier_distribution && a.tier_distribution.Budget) || 0) + "</td><td>" + ((b.tier_distribution && b.tier_distribution.Budget) || 0) + "</td></tr><tr><td>Mid-Tier</td><td>" + ((a.tier_distribution && a.tier_distribution["Mid-Tier"]) || 0) + "</td><td>" + ((b.tier_distribution && b.tier_distribution["Mid-Tier"]) || 0) + "</td></tr><tr><td>Luxury</td><td>" + ((a.tier_distribution && a.tier_distribution.Luxury) || 0) + "</td><td>" + ((b.tier_distribution && b.tier_distribution.Luxury) || 0) + "</td></tr></tbody></table>";
  const existing = document.getElementById("compare-block");
  if (existing) existing.remove();
  container.id = "compare-block";
  const cards = document.getElementById("cards");
  cards.insertBefore(container, cards.firstChild);
}
async function doSearch(query) {
  if (!query) return;
  showFeedback("");
  startLoading();
  try {
    const data = await fetchLocality(query);
    state.data = data;
    renderAll(data);
    if (state.compareMode && state.compareData) renderCompare();
    updateShareLink();
  } catch (err) { showFeedback("Could not reach the PlotWorth backend. " + err.message); }
  finally { stopLoading(); }
}
async function doCompareSearch(query) {
  if (!query) return;
  startLoading();
  try {
    state.compareData = await fetchLocality(query);
    if (state.data) renderCompare();
  } catch (err) { showFeedback("Comparison query failed. " + err.message); }
  finally { stopLoading(); }
}
function exportCSV() {
  const d = state.data;
  if (!d || !d.properties || !d.properties.length) { showFeedback("No properties to export yet."); return; }
  const headers = ["lat", "lng", "address", "type", "price_per_sqft", "bhk", "area_sqft", "tier"];
  const rows = [headers.join(",")];
  d.properties.forEach(function(p) {
    rows.push(headers.map(function(h) { const v = (p[h] === null || p[h] === undefined) ? "" : p[h]; const s = String(v).replace(/"/g, '""'); return /[",\n]/.test(s) ? '"' + s + '"' : s; }).join(","));
  });
  const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "plotworth_properties_" + (d.canonical || "locality").replace(/\s+/g, "_") + ".csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
function updateShareLink() {
  const q = state.data && state.data.query;
  if (!q) return;
  const url = new URL(window.location.href);
  url.searchParams.set("q", q);
  window.history.replaceState({}, "", url.toString());
}
function copyShareLink() {
  const q = state.data && state.data.query;
  if (!q) { showFeedback("Run a search first."); return; }
  const url = new URL(window.location.href);
  url.searchParams.set("q", q);
  navigator.clipboard.writeText(url.toString()).then(function() { showFeedback("Share link copied to clipboard."); }).catch(function() { showFeedback("Copy failed. URL: " + url.toString()); });
}
window.addEventListener("DOMContentLoaded", function() {
  $("search-btn").addEventListener("click", function() { doSearch($("search-input").value.trim()); });
  $("search-input").addEventListener("keydown", function(e) { if (e.key === "Enter") doSearch($("search-input").value.trim()); });
  $("compare-input").addEventListener("keydown", function(e) { if (e.key === "Enter") doCompareSearch($("compare-input").value.trim()); });
  $("geo-btn").addEventListener("click", function() {
    if (!navigator.geolocation) { showFeedback("Geolocation is not supported in this browser."); return; }
    startLoading();
    navigator.geolocation.getCurrentPosition(async function(pos) {
      try {
        const rev = await fetchReverse(pos.coords.latitude, pos.coords.longitude);
        const name = rev.canonical || rev.query || "";
        if (name) { $("search-input").value = name; await doSearch(name); }
      } catch (err) { showFeedback("Reverse geocoding failed. " + err.message); }
      finally { stopLoading(); }
    }, function() { showFeedback("Location permission denied."); stopLoading(); });
  });
  $("compare-toggle").addEventListener("change", function(e) {
    state.compareMode = e.target.checked;
    $("compare-input").classList.toggle("hidden", !state.compareMode);
    if (!state.compareMode) { state.compareData = null; const existing = document.getElementById("compare-block"); if (existing) existing.remove(); }
  });
  $("export-csv").addEventListener("click", exportCSV);
  $("share-btn").addEventListener("click", copyShareLink);
  const params = new URLSearchParams(window.location.search);
  const q = params.get("q");
  if (q) { $("search-input").value = q; doSearch(q); }
});