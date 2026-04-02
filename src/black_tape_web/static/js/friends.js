const friendsState = {
    categories: {},
    summary: {},
    ranking: {},
    activeCategory: "friends",
    selectedKey: "",
    query: "",
};

function friendById(id) {
    return document.getElementById(id);
}

function formatFriendCount(value) {
    return new Intl.NumberFormat("en-US").format(Number(value || 0));
}

function titleize(value) {
    return String(value || "")
        .split("_")
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

async function bootstrapFriends() {
    const searchNode = friendById("friends-search");
    if (searchNode) {
        searchNode.addEventListener("input", (event) => {
            friendsState.query = event.target.value.trim().toLowerCase();
            renderFriendList();
        });
    }

    await refreshFriends();
}

async function refreshFriends() {
    const jobId = localStorage.getItem("blacktape_job_id");
    const suffix = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";

    try {
        const response = await fetch(`/api/friends${suffix}`);
        const result = await response.json();
        if (result.status !== "SUCCESS") {
            return;
        }

        friendsState.categories = result.payload.categories || {};
        friendsState.summary = result.payload.summary || {};
        friendsState.ranking = result.payload.ranking || {};

        const availableCategories = Object.keys(friendsState.categories).filter((key) => (friendsState.categories[key] || []).length);
        friendsState.activeCategory = availableCategories.includes(friendsState.activeCategory)
            ? friendsState.activeCategory
            : (availableCategories[0] || "friends");
        friendsState.selectedKey = "";

        renderFriendSummary();
        renderCategoryBar();
        renderFriendList();
        renderInspector();
        syncSidebarReadouts();
    } catch (error) {
        console.error("Friends load failed", error);
        const list = friendById("friends-list");
        if (list) {
            list.innerHTML = `<div class="friends-empty-list">Unable to load friend data from the current vault.</div>`;
        }
    }
}

function renderFriendSummary() {
    const summary = friendsState.summary;
    const ranking = friendsState.ranking;
    const directCount = summary.friends || 0;
    const removedCount = summary.deleted_friends || 0;
    const blockedCount = summary.blocked_users || 0;
    const requestsCount = summary.friend_requests_sent || 0;

    friendById("friends-unique-count").textContent = formatFriendCount(summary.unique_usernames);
    friendById("friends-record-count").textContent = formatFriendCount(summary.total_records);
    friendById("friends-direct-count").textContent = formatFriendCount(directCount);
    friendById("friends-removed-count").textContent = formatFriendCount(removedCount);
    friendById("friends-blocked-count").textContent = formatFriendCount(blockedCount);
    friendById("friends-requests-count").textContent = formatFriendCount(requestsCount);
    friendById("friends-snapscore").textContent = formatFriendCount(ranking.snapscore);
}

function renderCategoryBar() {
    const node = friendById("friends-category-bar");
    if (!node) return;

    const categories = Object.entries(friendsState.categories).filter(([, entries]) => entries.length);
    if (!categories.length) {
        node.innerHTML = `<div class="friends-empty-list">No friend relationship files are available in the current vault.</div>`;
        return;
    }

    node.innerHTML = categories.map(([key, entries]) => `
        <button
            class="friends-category-btn${friendsState.activeCategory === key ? " active" : ""}"
            type="button"
            data-category="${key}"
        >
            ${titleize(key)} (${entries.length})
        </button>
    `).join("");

    node.querySelectorAll("[data-category]").forEach((button) => {
        button.addEventListener("click", () => {
            friendsState.activeCategory = button.dataset.category;
            friendsState.selectedKey = "";
            renderCategoryBar();
            renderFriendList();
            renderInspector();
        });
    });
}

function getVisibleFriends() {
    const active = friendsState.categories[friendsState.activeCategory] || [];
    if (!friendsState.query) return active;

    return active.filter((entry) => {
        const haystack = [
            entry.username,
            entry.display_name,
            entry.source,
        ].join(" ").toLowerCase();
        return haystack.includes(friendsState.query);
    });
}

function entryKey(entry) {
    return [entry.category, entry.username, entry.display_name, entry.created, entry.modified].join("|");
}

function renderFriendList() {
    const node = friendById("friends-list");
    if (!node) return;

    const visible = getVisibleFriends();
    if (!visible.length) {
        node.innerHTML = `<div class="friends-empty-list">No records match the current category and search filter.</div>`;
        return;
    }

    node.innerHTML = visible.map((entry) => {
        const key = entryKey(entry);
        const label = entry.display_name || entry.username || "Unnamed Profile";
        return `
            <article class="friend-card${friendsState.selectedKey === key ? " active" : ""}" data-key="${key}">
                <div class="friend-card-header">
                    <strong>${escapeHtml(label)}</strong>
                    <span>@${escapeHtml(entry.username || "unknown")}</span>
                </div>
                <div class="friend-meta-row">
                    <span>${titleize(entry.category)}</span>
                    <span>${escapeHtml(entry.source || "Source unavailable")}</span>
                </div>
            </article>
        `;
    }).join("");

    node.querySelectorAll(".friend-card").forEach((card) => {
        card.addEventListener("click", () => {
            friendsState.selectedKey = card.dataset.key;
            renderFriendList();
            renderInspector();
        });
    });
}

function renderInspector() {
    const node = friendById("friends-inspector");
    if (!node) return;

    const visible = getVisibleFriends();
    const selected = visible.find((entry) => entryKey(entry) === friendsState.selectedKey) || visible[0];
    if (!selected) {
        node.innerHTML = `<div class="friends-empty-state">Load a dataset with friend relationship files to review records here.</div>`;
        return;
    }

    friendsState.selectedKey = entryKey(selected);
    const label = selected.display_name || selected.username || "Unnamed Profile";

    node.innerHTML = `
        <section class="inspector-block">
            <h3 class="inspector-name">${escapeHtml(label)}</h3>
            <div class="inspector-row"><span class="micro-label">Username</span><span class="value">@${escapeHtml(selected.username || "unknown")}</span></div>
            <div class="inspector-row"><span class="micro-label">Bucket</span><span class="value">${escapeHtml(titleize(selected.category))}</span></div>
            <div class="inspector-row"><span class="micro-label">Source</span><span class="value">${escapeHtml(selected.source || "Unavailable")}</span></div>
            <div class="inspector-row"><span class="micro-label">Created</span><span class="value">${escapeHtml(selected.created || "Unavailable")}</span></div>
            <div class="inspector-row"><span class="micro-label">Last Modified</span><span class="value">${escapeHtml(selected.modified || "Unavailable")}</span></div>
        </section>
        <section class="inspector-block">
            <div class="inspector-row"><span class="micro-label">Category Records</span><span class="value">${formatFriendCount((friendsState.categories[selected.category] || []).length)}</span></div>
            <div class="inspector-row"><span class="micro-label">Vault Friend Count</span><span class="value">${formatFriendCount(friendsState.summary.friends)}</span></div>
            <div class="inspector-row"><span class="micro-label">Snapscore</span><span class="value">${formatFriendCount(friendsState.ranking.snapscore)}</span></div>
            <div class="inspector-row"><span class="micro-label">Reported Total Friends</span><span class="value">${formatFriendCount(friendsState.ranking.total_friends)}</span></div>
            <div class="inspector-row"><span class="micro-label">Reported Following</span><span class="value">${formatFriendCount(friendsState.ranking.following)}</span></div>
        </section>
    `;
}

function syncSidebarReadouts() {
    const jobId = localStorage.getItem("blacktape_job_id");
    if (friendById("session-readout") && jobId) {
        friendById("session-readout").textContent = jobId.slice(0, 8).toUpperCase();
    }
    if (friendById("header-load")) {
        friendById("header-load").textContent = `${formatFriendCount(friendsState.summary.unique_usernames)} FRIENDS`;
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

document.addEventListener("DOMContentLoaded", bootstrapFriends);
