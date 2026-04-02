const exploreState = {
    payload: {
        identity: [],
        google_signals: [],
        other: [],
    },
    query: "",
};

function exploreNode(id) {
    return document.getElementById(id);
}

function escapeExplore(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function exploreLoaderMarkup(copy = "Loading records") {
    return `
        <div class="bt-loader-copy">
            <span class="bt-loader bt-loader--tiles bt-loader--inline" aria-hidden="true">
                <span class="bt-loader__tile"></span>
                <span class="bt-loader__tile"></span>
                <span class="bt-loader__tile"></span>
                <span class="bt-loader__tile"></span>
            </span>
            <span>${escapeExplore(copy)}</span>
        </div>
    `;
}

function setExploreLoading() {
    ["explore-identity", "explore-google", "explore-other"].forEach((id) => {
        const node = exploreNode(id);
        if (!node) return;
        node.innerHTML = Array.from({ length: 3 }, () => `
            <article class="explore-item explore-item-loading">
                ${exploreLoaderMarkup("Loading records")}
            </article>
        `).join("");
    });
}

function exploreMatches(text) {
    if (!exploreState.query) return true;
    return String(text).toLowerCase().includes(exploreState.query);
}

function renderExploreSection(nodeId, items, formatter) {
    const node = exploreNode(nodeId);
    if (!node) return;
    if (!items.length) {
        node.innerHTML = `<div class="explore-item"><div>No matching records.</div></div>`;
        return;
    }
    node.innerHTML = items.map(formatter).join("");
}

function renderExplore() {
    renderExploreSection("explore-identity", exploreState.payload.identity.filter((item) => exploreMatches(`${item.key} ${item.value}`)), (item) => `
        <article class="explore-item">
            <strong>${item.key}</strong>
            <div>${item.value}</div>
        </article>
    `);

    renderExploreSection("explore-google", exploreState.payload.google_signals.filter((item) => exploreMatches(`${item.timestamp} ${item.kind} ${item.summary} ${JSON.stringify(item.details || {})}`)), (item) => `
        <article class="explore-item">
            <strong>${item.kind} :: ${item.timestamp}</strong>
            <div>${item.summary}</div>
            <div>${Object.entries(item.details || {}).slice(0, 4).map(([key, value]) => `${key}: ${value}`).join(" | ")}</div>
        </article>
    `);

    renderExploreSection("explore-other", exploreState.payload.other.filter((item) => exploreMatches(`${item.timestamp} ${item.type} ${item.summary} ${JSON.stringify(item.details || {})}`)), (item) => `
        <article class="explore-item">
            <strong>${item.type} :: ${item.timestamp}</strong>
            <div>${item.summary}</div>
            <div>${Object.entries(item.details || {}).map(([key, value]) => `${key}: ${value}`).join(" | ")}</div>
        </article>
    `);
}

async function loadExplore() {
    setExploreLoading();
    const jobId = localStorage.getItem("blacktape_job_id");
    const suffix = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
    const response = await fetch(`/api/explore${suffix}`);
    const result = await response.json();
    exploreState.payload = result.payload || { identity: [], google_signals: [], other: [] };
    renderExplore();
}

document.addEventListener("DOMContentLoaded", () => {
    const input = exploreNode("explore-search-input");
    if (input) {
        input.addEventListener("input", (event) => {
            exploreState.query = String(event.target.value || "").trim().toLowerCase();
            renderExplore();
        });
    }
    loadExplore();
});
