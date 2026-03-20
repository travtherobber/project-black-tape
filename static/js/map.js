/* ============================================================
   PROJECT BLACK-TAPE // REDLINE
   map.js - Geospatial Intelligence (Leaflet)
   ============================================================ */

let tacticalMap;
let tacticalPath;
let markers = [];

function initMap(lat = 0, lon = 0, zoom = 2) {
    console.log("[System] Initializing Tactical Map...");
    
    if (tacticalMap) {
        tacticalMap.remove();
    }

    tacticalMap = L.map('map-canvas', {
        zoomControl: false,
        attributionControl: false
    }).setView([lat, lon], zoom);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    }).addTo(tacticalMap);

    tacticalPath = L.polyline([], {
        color: 'var(--glow-purple)',
        weight: 2,
        opacity: 0.6,
        dashArray: '5, 10'
    }).addTo(tacticalMap);
}

function clearTacticalMap() {
    if (!tacticalMap) return;
    console.log("[System] Clearing Tactical Markers...");
    
    markers.forEach(m => {
        try {
            tacticalMap.removeLayer(m);
        } catch (e) {}
    });
    markers = [];
    
    if (tacticalPath) {
        tacticalPath.setLatLngs([]);
    }
}

function addTacticalMarker(lat, lon, popupText, type = 'system') {
    if (!tacticalMap) return null;

    const color = (type === 'system') ? '#39ff14' : '#00fff9';

    const icon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="background-color:${color}; width:12px; height:12px; border: 2px solid #000; border-radius:50%; box-shadow: 0 0 10px ${color};"></div>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6]
    });

    const marker = L.marker([lat, lon], { icon: icon })
        .addTo(tacticalMap)
        .bindPopup(`<span class="label-micro" style="color:var(--glow-mint); font-size:1rem; font-weight:bold; text-shadow: 1px 1px 2px #000;">${popupText}</span>`);

    markers.push(marker);
    return marker;
}

function drawChronologicalPath(points) {
    if (!tacticalPath) return;
    // Ensure points are sorted by timestamp before drawing path
    const sorted = [...points].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const latlngs = sorted.map(p => [p.lat, p.lon]);
    tacticalPath.setLatLngs(latlngs);
}
