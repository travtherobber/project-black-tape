let tacticalMap;
let markers = [];
let tacticalPaths = [];
let actionMarkers = [];

const layerVisuals = {
    location_history: { marker: "#86cfd1", glow: "rgba(134, 207, 209, 0.12)", path: "#86cfd1", dash: "6, 8", shape: "circle" },
    memories_history: { marker: "#d1b17b", glow: "rgba(209, 177, 123, 0.18)", path: "#d1b17b", dash: "2, 10", shape: "circle" },
    google_location_history: { marker: "#7fcf9c", glow: "rgba(127, 207, 156, 0.18)", path: "#7fcf9c", dash: "8, 6", shape: "circle" },
    google_timeline_edits: { marker: "#d29a63", glow: "rgba(210, 154, 99, 0.18)", path: "#d29a63", dash: "2, 6", shape: "diamond" },
    other: { marker: "#7f8a90", glow: "rgba(127, 138, 144, 0.18)", path: "#7f8a90", dash: "6, 8", shape: "circle" },
};

function initMap(lat = 0, lon = 0, zoom = 2) {
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

    window.tacticalMap = tacticalMap;
}

function clearTacticalMap() {
    if (!tacticalMap) return;
    markers.forEach(m => {
        try {
            tacticalMap.removeLayer(m);
        } catch (e) {}
    });
    markers = [];
    actionMarkers.forEach((marker) => {
        try {
            tacticalMap.removeLayer(marker);
        } catch (e) {}
    });
    actionMarkers = [];
    
    tacticalPaths.forEach((path) => {
        try {
            tacticalMap.removeLayer(path);
        } catch (e) {}
    });
    tacticalPaths = [];
}

function addTacticalMarker(lat, lon, popupText, layer = "other") {
    if (!tacticalMap) return null;

    const visual = layerVisuals[layer] || layerVisuals.other;
    const shapeStyle = visual.shape === "diamond"
        ? "border-radius:2px; transform: rotate(45deg);"
        : "border-radius:50%;";

    const icon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="background-color:${visual.marker}; width:12px; height:12px; border: 2px solid rgba(4, 12, 15, 0.92); ${shapeStyle} box-shadow: 0 0 0 4px ${visual.glow};"></div>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6]
    });

    const marker = L.marker([lat, lon], { icon: icon })
        .addTo(tacticalMap)
        .bindPopup(`<span style="color:#d9e5e7; font-size:0.95rem; line-height:1.5;">${popupText}</span>`);

    markers.push(marker);
    return marker;
}

function addActionMarker(lat, lon, popupText, kind = "other") {
    if (!tacticalMap) return null;
    const colorMap = {
        chat: "#49d8ff",
        friend: "#ffc857",
        google: "#ff9d57",
        other: "#c3ccd1",
    };
    const color = colorMap[kind] || colorMap.other;
    const icon = L.divIcon({
        className: "custom-div-icon action-div-icon",
        html: `
            <div style="position:relative; width:18px; height:18px;">
                <div style="position:absolute; inset:0; border-radius:999px; background:${color}; opacity:0.14;"></div>
                <div style="position:absolute; left:4px; top:4px; width:10px; height:10px; border-radius:999px; background:${color}; border:2px solid rgba(4, 12, 15, 0.92); box-shadow:0 0 0 4px ${color}1f;"></div>
            </div>
        `,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
    });

    const marker = L.marker([lat, lon], { icon })
        .addTo(tacticalMap)
        .bindPopup(`<span style="color:#d9e5e7; font-size:0.95rem; line-height:1.5;">${popupText}</span>`);

    actionMarkers.push(marker);
    return marker;
}

function drawChronologicalPaths(pointsByLayer) {
    if (!tacticalMap) return;
    Object.entries(pointsByLayer).forEach(([layer, points]) => {
        const sorted = [...points]
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
            .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lon));
        if (sorted.length < 2) return;
        const visual = layerVisuals[layer] || layerVisuals.other;
        const polyline = L.polyline(sorted.map((point) => [point.lat, point.lon]), {
            color: visual.path,
            weight: layer === "google_timeline_edits" ? 3 : 2,
            opacity: 0.72,
            dashArray: visual.dash,
        }).addTo(tacticalMap);
        tacticalPaths.push(polyline);
    });
}
