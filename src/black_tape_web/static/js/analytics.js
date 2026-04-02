function analyticsNode(id) {
    return document.getElementById(id);
}

function analyticsLoaderMarkup(copy = "Loading") {
    return `
        <div class="bt-loader-copy">
            <span class="bt-loader bt-loader--tiles bt-loader--inline" aria-hidden="true">
                <span class="bt-loader__tile"></span>
                <span class="bt-loader__tile"></span>
                <span class="bt-loader__tile"></span>
                <span class="bt-loader__tile"></span>
            </span>
            <span>${copy}</span>
        </div>
    `;
}

function setAnalyticsLoading() {
    ["analytics-messages", "analytics-conversations", "analytics-gps", "analytics-google-signals"].forEach((id) => {
        const node = analyticsNode(id);
        if (node) node.textContent = "--";
    });

    [
        "analytics-top-conversations",
        "analytics-gps-layers",
        "analytics-google-activity",
        "analytics-friends-summary",
        "analytics-busiest-days",
    ].forEach((id) => {
        const node = analyticsNode(id);
        if (!node) return;
        node.innerHTML = Array.from({ length: 3 }, () => `
            <div class="analytics-item analytics-item-loading">
                ${analyticsLoaderMarkup("Loading metrics")}
            </div>
        `).join("");
    });
}

function renderAnalyticsList(nodeId, items, labelKey, valueKey) {
    const node = analyticsNode(nodeId);
    if (!node) return;
    if (!items.length) {
        node.innerHTML = `<div class="analytics-item"><span>No data available</span></div>`;
        return;
    }
    node.innerHTML = items.map((item) => `
        <div class="analytics-item">
            <span>${String(item[labelKey] ?? "Unknown")}</span>
            <strong>${String(item[valueKey] ?? 0)}</strong>
        </div>
    `).join("");
}

async function loadAnalytics() {
    setAnalyticsLoading();
    const jobId = localStorage.getItem("blacktape_job_id");
    const suffix = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
    const response = await fetch(`/api/analytics${suffix}`);
    const result = await response.json();
    const payload = result.payload || {};
    const overview = payload.overview || {};

    analyticsNode("analytics-messages").textContent = String(overview.messages || 0);
    analyticsNode("analytics-conversations").textContent = String(overview.conversations || 0);
    analyticsNode("analytics-gps").textContent = String(overview.gps_points || 0);
    analyticsNode("analytics-google-signals").textContent = String(overview.google_signals || 0);

    renderAnalyticsList("analytics-top-conversations", payload.chat?.top_conversations || [], "conversation", "messages");
    renderAnalyticsList(
        "analytics-gps-layers",
        Object.entries(payload.gps?.layers || {}).map(([layer, count]) => ({ layer, count })),
        "layer",
        "count",
    );
    renderAnalyticsList("analytics-google-activity", payload.google?.top_activities || [], "activity", "count");
    renderAnalyticsList(
        "analytics-friends-summary",
        Object.entries(payload.friends?.summary || {}).map(([metric, count]) => ({ metric, count })),
        "metric",
        "count",
    );
    renderAnalyticsList("analytics-busiest-days", payload.gps?.busiest_days || [], "day", "points");
}

document.addEventListener("DOMContentLoaded", loadAnalytics);
