/**
 * Chat Viewer Module - Project Black-Tape
 * Manages conversation state, interactive search, and real-time UI rendering.
 * REVISION: Generic Identity Support & Enhanced Scroll Tracking.
 * STATUS: SIGNAL_STABLE
 */

const state = {
    conversations: [],
    activeConversation: null,
    activeMessages: [],
    isSidebarCollapsed: false,
    sortOrder: 'newest',
    endpoints: {
        list: "/api/conversations",
        details: "/api/conversations/", // + convo_id
        search: "/api/search"
    }
};

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

/**
 * Module Initialization
 */
document.addEventListener("DOMContentLoaded", async () => {
    console.log("[Module] Chat Viewer initialized.");

    const searchInput = document.getElementById('contactSearch');
    if (searchInput) {
        const seededQuery = localStorage.getItem("blacktape_search_seed");
        if (seededQuery) {
            searchInput.value = seededQuery;
            localStorage.removeItem("blacktape_search_seed");
        }
        searchInput.addEventListener("input", debounce((e) => {
            searchMessages(e.target.value);
        }, 300));
    }

    // Handle Timezone Shifts (Global Event)
    window.addEventListener('timezoneChanged', () => {
        if (state.activeMessages.length > 0) {
            renderMessages(state.activeMessages);
        }
    });

    // Initial Vault Sync
    await syncConversations();

    if (searchInput && searchInput.value.trim().length >= 2) {
        searchMessages(searchInput.value.trim());
    }

    syncSortButtons();

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".floating-controls")) {
            collapseFabs();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            collapseFabs();
        }
    });
});

/**
 * Utility: Debounce for search to prevent API flooding
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Data Synchronization
 * Pulls jobId from localStorage to ensure DiskCache alignment.
 */
async function syncConversations() {
    const jobId = localStorage.getItem('blacktape_job_id');

    if (!jobId) {
        renderPlaceholder("NO_ACTIVE_JOB_ID // INGESTION_REQUIRED");
        return;
    }

    try {
        const response = await fetch(`${state.endpoints.list}?job_id=${jobId}`);
        const result = await response.json();

        if (result.status === "SUCCESS") {
            state.conversations = result.payload;
            renderContactList();
            if (window.logToTerminal) {
                window.logToTerminal(`Vault synced. ${state.conversations.length} clusters identified.`, "OK");
            }
        } else if (result.status === "PROCESSING") {
            renderPlaceholder("VAULT_IN_PROGRESS // SIPHONING...");
            // Poll for completion
            setTimeout(syncConversations, 2000);
        } else {
            renderPlaceholder("VAULT_EMPTY // RE-UPLOAD_SIGNAL");
        }
    } catch (err) {
        console.error("Sync error:", err);
        renderPlaceholder("CONNECTION_FAILURE // BACKEND_OFFLINE");
    }
}

/**
 * UI Rendering: Sidebar
 */
function renderContactList() {
    const list = document.getElementById("contactList");
    if (!list) return;

    if (state.conversations.length === 0) {
        list.innerHTML = `<div class="status-msg">NO_SIGNALS_FOUND</div>`;
        return;
    }

    const fragment = document.createDocumentFragment();
    state.conversations.forEach(convo => {
        const card = document.createElement("div");
        card.className = "contact-card";
        card.dataset.id = convo.id;

        // Handle fallback for unclassified clusters
        const displayName = convo.id === "GENERAL_SIGNAL" ? "UNCLASSIFIED_CHAT" : convo.id;

        card.innerHTML = `
            <span class="contact-name">${escapeHtml(displayName.toUpperCase())}</span>
            <span class="contact-meta">${escapeHtml(`${convo.count ?? convo.messageCount ?? 0} MESSAGES // READY`)}</span>
        `;

        card.onclick = () => selectConversation(convo.id);
        fragment.appendChild(card);
    });

    list.innerHTML = "";
    list.appendChild(fragment);
}

/**
 * Selection Logic: Message Retrieval
 * Appends jobId to detail request to maintain cache persistence.
 */
async function selectConversation(id, targetTimestamp = null) {
    const jobId = localStorage.getItem('blacktape_job_id');
    state.activeConversation = id;

    // UI State Feedback
    document.querySelectorAll(".contact-card").forEach(c => c.classList.remove("active"));
    const activeCard = document.querySelector(`.contact-card[data-id="${id}"]`);
    if (activeCard) activeCard.classList.add("active");

    const label = document.getElementById("active-target-id");
    if (label) label.textContent = `TARGET: ${id.toUpperCase()}`;

    // Show loading state if we aren't jumping to a specific search result
    if (!targetTimestamp) renderPlaceholder("SIPHONING_DATA_PACKETS...");

    try {
        const response = await fetch(`${state.endpoints.details}${encodeURIComponent(id)}?job_id=${jobId}`);
        const result = await response.json();

        if (result.status === "SUCCESS") {
            state.activeMessages = result.payload;
            renderMessages(state.activeMessages, targetTimestamp);
        } else {
            renderPlaceholder("FAULT: SIGNAL_INACCESSIBLE");
        }
    } catch (err) {
        console.error("Fetch error:", err);
        renderPlaceholder("CRITICAL_FAULT: SIGNAL_LOST");
    }
}

/**
 * UI Rendering: Message View
 */
function renderMessages(messages, targetTimestamp = null) {
    const container = document.getElementById("chatViewerContainer");
    if (!container) return;

    container.innerHTML = "";

    // Apply Sorting based on UI state
    const sortedMessages = [...messages].sort((a, b) => {
        const timeA = new Date(a.Created);
        const timeB = new Date(b.Created);
        return state.sortOrder === 'newest' ? timeB - timeA : timeA - timeB;
    });

    let lastDate = null;
    let targetElement = null;

    sortedMessages.forEach(msg => {
        // Convert to local time using global helper (main.js / utils.js)
        const localTs = window.convertToLocal ? window.convertToLocal(msg.Created) : msg.Created;
        const datePart = localTs.split(" ")[0];

        // Date Headers (Separators)
        if (datePart !== lastDate) {
            const separator = document.createElement("div");
            separator.className = "date-header";
            separator.textContent = datePart;
            container.appendChild(separator);
            lastDate = datePart;
        }

        const block = document.createElement("div");
        block.className = `message-block ${msg.IsSender ? "outbound" : "incoming"}`;

        // Identity Labeling
        const senderLabel = (!msg.IsSender) ? `<div class="sender-name">${msg.SenderName || 'Remote_Entity'}</div>` : "";
        const safeSenderLabel = (!msg.IsSender) ? `<div class="sender-name">${escapeHtml(msg.SenderName || 'Remote_Entity')}</div>` : "";

        block.innerHTML = `
            ${safeSenderLabel}
            <div class="message-content">${escapeHtml(msg.Content)}</div>
            <span class="timestamp">${escapeHtml(localTs.replace(' ', ' | '))}</span>
        `;

        block.onclick = () => showMetadata(msg, localTs);
        container.appendChild(block);

        // Tracking for search-to-message navigation
        if (targetTimestamp && msg.Created === targetTimestamp) {
            targetElement = block;
        }
    });

    // Smooth Scroll & Highlight Logic
    if (targetElement) {
        setTimeout(() => {
            targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            targetElement.classList.add("message-highlight");
            setTimeout(() => targetElement.classList.remove("message-highlight"), 3000);
        }, 150);
    } else {
        // Default scroll behavior based on sort order
        container.scrollTop = state.sortOrder === 'newest' ? 0 : container.scrollHeight;
    }
}

/**
 * Search Logic
 * Interrogates the vault via the backend Search Engine.
 */
async function searchMessages(query) {
    const jobId = localStorage.getItem('blacktape_job_id');
    const list = document.getElementById("contactList");
    if (!list || !jobId) return;

    if (!query || query.trim().length < 2) {
        renderContactList(); // Revert to standard sidebar
        return;
    }

    try {
        const response = await fetch(`${state.endpoints.search}?q=${encodeURIComponent(query)}&job_id=${jobId}`);
        const data = await response.json();

        if (data.status !== "SUCCESS" || !data.results || data.results.length === 0) {
            list.innerHTML = `<div class="status-msg">NO_MATCHES_FOUND</div>`;
            return;
        }

        list.innerHTML = `<div class="status-msg" style="padding: 10px; color: var(--accent-orange);">MATCHES: ${data.results.length}</div>`;

        data.results.forEach(res => {
            const card = document.createElement("div");
            card.className = "contact-card search-result-card";
            card.innerHTML = `
                <span class="contact-name">${escapeHtml(res.convoId.toUpperCase())}</span>
                <span class="contact-meta" style="color: var(--accent-orange); overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">
                    ${escapeHtml(res.message.Content)}
                </span>
            `;
            // Jump directly to the conversation and message
            card.onclick = () => selectConversation(res.convoId, res.message.Created);
            list.appendChild(card);
        });

    } catch (err) {
        console.error("Search failed:", err);
        list.innerHTML = `<div class="status-msg">SEARCH_ERROR</div>`;
    }
}

/**
 * UI Component: Metadata Overlay (Intel Siphon)
 */
function showMetadata(msg, localTs) {
    const overlay = document.createElement("div");
    overlay.className = "metadata-overlay";

    // Industrial styling for raw metadata dump
    const rawData = JSON.stringify(msg.Metadata || {}, null, 4);

    overlay.innerHTML = `
        <div class="metadata-card">
            <div class="card-header">
                <h3>SIGNAL_INTEL // METADATA</h3>
                <button onclick="this.closest('.metadata-overlay').remove()">[X]</button>
            </div>
            <div class="card-body">
                <div class="intel-group"><label>Timestamp (Local)</label><span>${escapeHtml(localTs)}</span></div>
                <div class="intel-group"><label>Cluster_ID</label><span>${escapeHtml(state.activeConversation)}</span></div>
                <div class="intel-group"><label>Signal_Origin</label><span>${escapeHtml(msg.IsSender ? "SYSTEM_OWNER" : "REMOTE_ENTITY")}</span></div>
                <hr style="border: 0; border-top: 1px dashed var(--border-color); margin: 15px 0;">
                <div style="font-size: 0.8rem; color: var(--text-dim); margin-bottom: 5px;">RAW_METADATA_STREAM:</div>
                <pre>${escapeHtml(rawData)}</pre>
            </div>
        </div>
    `;
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    document.body.appendChild(overlay);
}

/**
 * Helper: Placeholder Rendering
 */
function renderPlaceholder(text) {
    const container = document.getElementById("chatViewerContainer");
    if (container) container.innerHTML = `<div class="status-msg">${text}</div>`;
}

function toggleFab(groupId) {
    document.querySelectorAll(".fab-group").forEach((group) => {
        group.classList.toggle("expanded", group.id === groupId && !group.classList.contains("expanded"));
    });
}

function changeSort(order) {
    state.sortOrder = order;
    syncSortButtons();

    if (state.activeMessages.length > 0) {
        renderMessages(state.activeMessages);
    }

    collapseFabs();
}

function syncSortButtons() {
    document.querySelectorAll(".sort-options button").forEach((button) => {
        const normalized = button.textContent.trim().toLowerCase();
        button.classList.toggle("active", normalized === state.sortOrder);
    });
}

function collapseFabs() {
    document.querySelectorAll(".fab-group").forEach((group) => {
        group.classList.remove("expanded");
    });
}

window.toggleFab = toggleFab;
window.changeSort = changeSort;
