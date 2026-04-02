const timelineState = {
    allItems: [],
    filteredItems: [],
    groupedDays: [],
    activeDay: "",
    activeEventId: "",
    kindFilter: "all",
    searchQuery: "",
    visibleDayLimit: 36,
};

function timelineNode(id) {
    return document.getElementById(id);
}

function timelineConvert(timestamp) {
    return window.convertToLocal ? window.convertToLocal(timestamp) : timestamp;
}

function timelineDateKey(timestamp) {
    return timelineConvert(timestamp).split(" ")[0];
}

function timelineTimeOnly(timestamp) {
    return timelineConvert(timestamp).split(" ")[1] || "";
}

function eventKindClass(kind) {
    if (kind === "chat" || kind === "gps" || kind === "friend") {
        return kind;
    }
    return "other";
}

function describeTimelineEvent(item) {
    const time = timelineTimeOnly(item.timestamp);

    if (item.kind === "chat") {
        const sender = item.details?.sender || "unknown";
        const direction = item.details?.direction === "outbound" ? "Chat to" : "Chat from";
        return `${time} ${direction} ${sender}`;
    }

    if (item.kind === "gps") {
        const coords = item.details?.coordinates || "GPS point";
        return `${time} Location updated ${coords}`;
    }

    if (item.kind === "friend") {
        const name = item.details?.display_name || item.details?.username || "unknown";
        const action = item.details?.event === "modified" ? "Friend updated" : "Friend event";
        return `${time} ${action} ${name}`;
    }

    return `${time} ${item.summary}`;
}

function normalizeTimelineText(item) {
    return [
        item.kind,
        item.label,
        item.summary,
        ...Object.values(item.details || {}),
    ].join(" ").toLowerCase();
}

async function bootstrapTimeline() {
    wireTimelineFilters();
    await refreshTimeline();
}

async function refreshTimeline() {
    const jobId = localStorage.getItem("blacktape_job_id");
    const suffix = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";

    try {
        const response = await fetch(`/api/timeline${suffix}`);
        const result = await response.json();
        timelineState.allItems = result.status === "SUCCESS" ? (result.payload || []) : [];
        applyTimelineFilters();
    } catch (error) {
        console.error("Timeline load failed", error);
        timelineState.allItems = [];
        applyTimelineFilters();
    }
}

function applyTimelineFilters() {
    const query = timelineState.searchQuery.trim().toLowerCase();
    timelineState.filteredItems = timelineState.allItems.filter((item) => {
        if (timelineState.kindFilter !== "all" && item.kind !== timelineState.kindFilter) {
            return false;
        }
        if (!query) {
            return true;
        }
        return normalizeTimelineText(item).includes(query);
    });

    const grouped = new Map();
    timelineState.filteredItems.forEach((item) => {
        const key = timelineDateKey(item.timestamp);
        if (!grouped.has(key)) {
            grouped.set(key, []);
        }
        grouped.get(key).push(item);
    });

    timelineState.groupedDays = [...grouped.entries()]
        .map(([day, items]) => ({
            day,
            items: items.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)),
        }))
        .sort((a, b) => b.day.localeCompare(a.day));

    if (!timelineState.groupedDays.some((entry) => entry.day === timelineState.activeDay)) {
        timelineState.activeDay = timelineState.groupedDays[0]?.day || "";
    }

    const activeItems = getActiveDayItems();
    if (!activeItems.some((item) => item.id === timelineState.activeEventId)) {
        timelineState.activeEventId = activeItems[0]?.id || "";
    }

    renderTimelineSummary();
    renderTimelineDayGrid();
    renderTimelineDayDetail();
    syncTimelineFilterChips();
}

function renderTimelineSummary() {
    timelineNode("timeline-day-count").textContent = String(timelineState.groupedDays.length);
    timelineNode("timeline-total-count").textContent = String(timelineState.filteredItems.length);
    timelineNode("timeline-filter-count").textContent = `${timelineState.filteredItems.length} visible`;

    if (!timelineState.filteredItems.length) {
        timelineNode("timeline-range-label").textContent = "No timeline data loaded.";
        return;
    }

    const oldest = timelineConvert(timelineState.filteredItems[0].timestamp);
    const newest = timelineConvert(timelineState.filteredItems[timelineState.filteredItems.length - 1].timestamp);
    timelineNode("timeline-range-label").textContent = `Oldest ${oldest} to newest ${newest}`;
}

function renderTimelineDayGrid() {
    const grid = timelineNode("timeline-day-grid");
    if (!grid) return;

    if (!timelineState.groupedDays.length) {
        grid.innerHTML = `<div class="timeline-empty-state">No days match the current filters.</div>`;
        return;
    }

    const limitedDays = timelineState.groupedDays.slice(0, timelineState.visibleDayLimit);
    grid.innerHTML = limitedDays.map((entry) => {
        const first = timelineTimeOnly(entry.items[0].timestamp);
        const last = timelineTimeOnly(entry.items[entry.items.length - 1].timestamp);
        const preview = entry.items.slice(0, 3).map((item) => `
            <div class="timeline-day-preview timeline-kind-${eventKindClass(item.kind)}">
                <span class="timeline-day-preview-time">${escapeTimeline(timelineTimeOnly(item.timestamp))}</span>
                <span>${escapeTimeline(describeTimelineEvent(item).replace(`${timelineTimeOnly(item.timestamp)} `, ""))}</span>
            </div>
        `).join("");
        return `
            <button class="timeline-day-card${timelineState.activeDay === entry.day ? " active" : ""}" type="button" data-day="${entry.day}">
                <strong>${escapeTimeline(entry.day)}</strong>
                <div class="micro-label">${entry.items.length} events</div>
                <div class="timeline-day-preview-stack">${preview}</div>
                <div class="timeline-day-card-meta">
                    <span>First ${escapeTimeline(first || "--:--:--")}</span>
                    <span>Last ${escapeTimeline(last || "--:--:--")}</span>
                </div>
            </button>
        `;
    }).join("");

    grid.querySelectorAll("[data-day]").forEach((button) => {
        button.addEventListener("click", () => {
            timelineState.activeDay = button.dataset.day;
            timelineState.activeEventId = getActiveDayItems()[0]?.id || "";
            renderTimelineDayGrid();
            renderTimelineDayDetail();
        });
    });
}

function renderTimelineDayDetail() {
    const node = timelineNode("timeline-day-detail-body");
    if (!node) return;

    const dayEntry = timelineState.groupedDays.find((entry) => entry.day === timelineState.activeDay);
    if (!dayEntry) {
        node.innerHTML = `<div class="timeline-empty-state">Select a day card to inspect its 24-hour activity and event sequence.</div>`;
        return;
    }

    const items = dayEntry.items;
    const activeEvent = items.find((item) => item.id === timelineState.activeEventId) || items[0];
    if (activeEvent) {
        timelineState.activeEventId = activeEvent.id;
    }

    const graphDots = items.map((item) => {
        const hour = eventHourPosition(item.timestamp);
        return `
            <button
                class="timeline-day-dot is-${item.kind}${item.id === timelineState.activeEventId ? " active" : ""}"
                type="button"
                data-event-id="${item.id}"
                style="left:${hour}%;"
                title="${escapeTimeline(timelineTimeOnly(item.timestamp))} ${escapeTimeline(item.summary)}"
            ></button>
        `;
    }).join("");

    const tickLabels = [0, 6, 12, 18, 24].map((hour) => `
        <div class="timeline-day-graph-tick" style="left:${(hour / 24) * 100}%;">${String(hour).padStart(2, "0")}:00</div>
    `).join("");

    const listItems = items.map((item) => `
        <article class="timeline-day-item timeline-kind-${eventKindClass(item.kind)}${item.id === timelineState.activeEventId ? " active" : ""}" data-event-id="${item.id}">
            <div class="timeline-day-item-top">
                <span class="timeline-kind-label timeline-kind-${eventKindClass(item.kind)}">${escapeTimeline(item.kind.toUpperCase())}</span>
                <span>${escapeTimeline(timelineTimeOnly(item.timestamp))}</span>
            </div>
            <div class="timeline-day-item-summary">${escapeTimeline(describeTimelineEvent(item))}</div>
        </article>
    `).join("");

    const detailRows = Object.entries(activeEvent?.details || {}).map(([key, value]) => `
        <div class="timeline-day-item-top">
            <span class="micro-label">${escapeTimeline(key.replaceAll("_", " "))}</span>
            <span>${escapeTimeline(String(value))}</span>
        </div>
    `).join("");

    node.innerHTML = `
        <section class="timeline-detail-block">
            <div class="timeline-detail-heading">
                <div>
                    <h3 class="timeline-detail-title">${escapeTimeline(dayEntry.day)}</h3>
                    <div class="micro-label">${items.length} events in chronological order</div>
                </div>
                <div class="timeline-detail-nav">
                    <button class="selector-pill" id="timeline-prev-button" type="button" onclick="stepTimelineSelection(-1)">Previous</button>
                    <button class="selector-pill" id="timeline-next-button" type="button" onclick="stepTimelineSelection(1)">Next</button>
                </div>
            </div>
            <div class="timeline-day-graph">
                <div class="timeline-day-graph-line"></div>
                ${tickLabels}
                ${graphDots}
            </div>
        </section>
        <section class="timeline-detail-block">
            <div class="timeline-detail-heading">
                <div>
                    <h3 class="timeline-detail-title">${escapeTimeline(activeEvent?.summary || "No event selected")}</h3>
                    <div class="micro-label">${escapeTimeline(activeEvent ? timelineConvert(activeEvent.timestamp) : "")}</div>
                </div>
            </div>
            ${detailRows || `<div class="timeline-empty-state">No extra detail fields for this event.</div>`}
        </section>
        <section class="timeline-detail-block">
            <div class="timeline-detail-heading">
                <div>
                    <h3 class="timeline-detail-title">Daily Event List</h3>
                    <div class="micro-label">Oldest to newest within the selected day</div>
                </div>
            </div>
            <div class="timeline-day-list">${listItems}</div>
        </section>
    `;

    node.querySelectorAll("[data-event-id]").forEach((item) => {
        item.addEventListener("click", () => {
            timelineState.activeEventId = item.dataset.eventId;
            renderTimelineDayDetail();
        });
    });

    updateTimelineNavState();
}

function getActiveDayItems() {
    return timelineState.groupedDays.find((entry) => entry.day === timelineState.activeDay)?.items || [];
}

function stepTimelineSelection(direction) {
    const items = getActiveDayItems();
    if (!items.length) return;

    let index = items.findIndex((item) => item.id === timelineState.activeEventId);
    if (index === -1) {
        index = direction > 0 ? -1 : 0;
    }

    const nextIndex = Math.min(items.length - 1, Math.max(0, index + direction));
    timelineState.activeEventId = items[nextIndex].id;
    renderTimelineDayDetail();
}

function updateTimelineNavState() {
    const items = getActiveDayItems();
    const index = items.findIndex((item) => item.id === timelineState.activeEventId);
    const prev = timelineNode("timeline-prev-button");
    const next = timelineNode("timeline-next-button");
    if (prev) prev.disabled = index <= 0;
    if (next) next.disabled = index === -1 || index >= items.length - 1;
}

function wireTimelineFilters() {
    const input = timelineNode("timeline-search-input");
    if (input) {
        input.addEventListener("input", debounceTimeline((event) => {
            timelineState.searchQuery = event.target.value;
            applyTimelineFilters();
        }, 160));
    }
}

function setTimelineKindFilter(kind) {
    timelineState.kindFilter = kind;
    applyTimelineFilters();
}

function resetTimelineFilters() {
    timelineState.kindFilter = "all";
    timelineState.searchQuery = "";
    const input = timelineNode("timeline-search-input");
    if (input) input.value = "";
    applyTimelineFilters();
}

function syncTimelineFilterChips() {
    document.querySelectorAll(".timeline-filter-chip").forEach((chip) => {
        chip.classList.toggle("active", chip.dataset.kind === timelineState.kindFilter);
    });
}

function eventHourPosition(timestamp) {
    const parts = timelineConvert(timestamp).split(" ");
    const time = parts[1] || "00:00:00";
    const [hour, minute, second] = time.split(":").map((value) => Number(value) || 0);
    return ((hour * 3600) + (minute * 60) + second) / 86400 * 100;
}

function debounceTimeline(func, wait) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = window.setTimeout(() => func(...args), wait);
    };
}

function escapeTimeline(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

document.addEventListener("DOMContentLoaded", bootstrapTimeline);
window.setTimelineKindFilter = setTimelineKindFilter;
window.resetTimelineFilters = resetTimelineFilters;
window.stepTimelineSelection = stepTimelineSelection;
