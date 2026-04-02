const FEED_ITEMS = [
    {
        time: "00:00:00",
        kind: "STANDBY",
        message: "Console armed. Upload a parcel to begin indexing.",
        note: "Vault currently empty.",
    },
];

const dashboardState = {
    activeJobId: localStorage.getItem("blacktape_job_id") || "",
    activeFileName: "",
    activeStatus: "IDLE",
    lastUpdate: "",
    lastFeedKey: "",
    lastPolledStatus: "",
    isUploading: false,
    summary: {
        messages: 0,
        conversations: 0,
        gps: 0,
    },
    pollTimer: null,
};

function byId(id) {
    return document.getElementById(id);
}

function setText(id, value) {
    const node = byId(id);
    if (node) node.textContent = value;
}

function setUploadLoading(isLoading, statusText) {
    const dropzone = byId("dropzone");
    const loader = byId("upload-loader");
    const status = byId("dropzone-status");

    if (dropzone) {
        dropzone.classList.toggle("is-busy", Boolean(isLoading));
    }
    if (loader) {
        loader.hidden = !isLoading;
    }
    if (statusText && status) {
        status.textContent = statusText;
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

function nowStamp() {
    return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function shortJob(jobId) {
    return jobId ? jobId.slice(0, 8).toUpperCase() : "NO LOCK";
}

function appendFeed(kind, message, note) {
    const feedKey = `${kind}|${message}|${note}`;
    if (dashboardState.lastFeedKey === feedKey) {
        return;
    }

    dashboardState.lastFeedKey = feedKey;
    FEED_ITEMS.unshift({ time: nowStamp(), kind, message, note });
    FEED_ITEMS.splice(18);
    dashboardState.lastUpdate = nowStamp();
    renderFeed();
    updateCounters();
}

function renderFeed() {
    const container = byId("telemetry-feed");
    if (!container) return;

    container.innerHTML = FEED_ITEMS.map((item) => `
        <div class="feed-entry feed-entry-${item.kind.toLowerCase()}">
            <div class="feed-time">${escapeHtml(item.time)}</div>
            <div class="feed-body">
                <span class="feed-kind">${escapeHtml(item.kind)}</span>
                <div class="feed-message">${escapeHtml(item.message)}</div>
                <div class="feed-note">${escapeHtml(item.note)}</div>
            </div>
        </div>
    `).join("");

    setText("feed-state", dashboardState.activeStatus);
}

function updateCounters() {
    setText("messages-total", String(dashboardState.summary.messages).padStart(4, "0"));
    setText("conversations-total", String(dashboardState.summary.conversations).padStart(2, "0"));
    setText("gps-total", String(dashboardState.summary.gps).padStart(4, "0"));
    setText("vault-state", dashboardState.activeStatus);
    setText("hero-job-id", shortJob(dashboardState.activeJobId));
    setText("hero-source-file", dashboardState.activeFileName || "NO DATASET");
    setText("feed-summary-update", dashboardState.lastUpdate || "NO LINK");
    setText("session-readout", shortJob(dashboardState.activeJobId));
    setText("header-ingest-state", dashboardState.activeStatus);
    setText("header-last-update", dashboardState.lastUpdate || "NO LINK");
    setText("header-load", `${dashboardState.summary.messages} MSG`);
    if (!dashboardState.isUploading) {
        setText("dropzone-status", dashboardState.activeStatus === "COMPLETE" ? "VAULT_LINK_ACTIVE" : "READY_FOR_SIGNAL_HANDOFF");
    }
}

async function loadConversations() {
    if (!dashboardState.activeJobId) {
        dashboardState.summary.conversations = 0;
        updateCounters();
        return;
    }

    const response = await fetch(`/api/conversations?job_id=${encodeURIComponent(dashboardState.activeJobId)}`);
    const result = await response.json();
    dashboardState.summary.conversations = result.status === "SUCCESS" ? (result.payload || []).length : 0;
    updateCounters();
}

async function loadGps() {
    if (!dashboardState.activeJobId) {
        dashboardState.summary.gps = 0;
        updateCounters();
        return;
    }

    const response = await fetch(`/api/gps?job_id=${encodeURIComponent(dashboardState.activeJobId)}`);
    const result = await response.json();
    dashboardState.summary.gps = result.status === "SUCCESS" ? (result.payload || []).length : 0;
    updateCounters();
}

async function pollVaultStatus(fileName, jobId) {
    if (dashboardState.pollTimer) {
        window.clearTimeout(dashboardState.pollTimer);
        dashboardState.pollTimer = null;
    }

    try {
        const response = await fetch(`/api/vault/status?job_id=${encodeURIComponent(jobId)}`);
        const status = await response.json();

        dashboardState.activeJobId = jobId;
        dashboardState.activeFileName = fileName || dashboardState.activeFileName;
        dashboardState.activeStatus = status.status || "UNKNOWN";
        dashboardState.lastUpdate = status.last_update
            ? new Date(status.last_update * 1000).toLocaleTimeString("en-US", { hour12: false })
            : nowStamp();
        dashboardState.summary.messages = Number(status.messages_found || 0);
        dashboardState.summary.gps = Number(status.gps_found || 0);
        updateCounters();

        if (status.status === "COMPLETE") {
            if (dashboardState.lastPolledStatus !== "COMPLETE") {
                appendFeed("COMPLETE", `${fileName} indexed successfully.`, `${dashboardState.summary.messages} messages and ${dashboardState.summary.gps} GPS points recovered.`);
            }
            dashboardState.lastPolledStatus = "COMPLETE";
            dashboardState.isUploading = false;
            setUploadLoading(false, "VAULT_LINK_ACTIVE");
            await Promise.all([loadConversations(), loadGps()]);
            return;
        }

        if (status.status === "FAILED" || status.status === "ERROR") {
            if (dashboardState.lastPolledStatus !== status.status) {
                appendFeed("FAULT", `${fileName} failed during ingestion.`, status.message || "Backend fault.");
            }
            dashboardState.lastPolledStatus = status.status;
            dashboardState.isUploading = false;
            setUploadLoading(false, "UPLOAD_FAULT_DETECTED");
            return;
        }

        const progressNote = `${dashboardState.summary.messages} messages and ${dashboardState.summary.gps} GPS points recovered so far.`;
        if (
            dashboardState.lastPolledStatus !== "PROCESSING" ||
            !FEED_ITEMS[0] ||
            FEED_ITEMS[0].note !== progressNote
        ) {
            appendFeed("PROCESS", `${fileName} is processing.`, progressNote);
        }
        dashboardState.lastPolledStatus = "PROCESSING";
        setUploadLoading(true, "INDEXING_PAYLOAD");
        dashboardState.pollTimer = window.setTimeout(() => pollVaultStatus(fileName, jobId), 1800);
    } catch (error) {
        console.error("Status poll failed:", error);
        dashboardState.activeStatus = "STATUS LOST";
        dashboardState.isUploading = false;
        setUploadLoading(false, "STATUS_LINK_LOST");
        updateCounters();
    }
}

function wireUpload() {
    const dropzone = byId("dropzone");
    const input = byId("ingest-file");
    const button = byId("ingest-button");
    if (!dropzone || !input || !button) return;

    const acceptFiles = async (files) => {
        if (dashboardState.isUploading) {
            appendFeed("FAULT", "Upload blocked while another ingest is active.", "Wait for the current archive to finish or fail.");
            return;
        }

        const selectedFiles = Array.from(files || []).filter(Boolean);
        if (!selectedFiles.length) return;
        const primaryFile = selectedFiles[0];
        const uploadLabel = selectedFiles.length === 1
            ? primaryFile.name
            : `${primaryFile.name} +${selectedFiles.length - 1} more`;

        dashboardState.isUploading = true;
        dashboardState.lastPolledStatus = "";
        dashboardState.lastFeedKey = "";
        if (dashboardState.pollTimer) {
            window.clearTimeout(dashboardState.pollTimer);
            dashboardState.pollTimer = null;
        }

        dashboardState.activeFileName = uploadLabel;
        dashboardState.activeStatus = "UPLINK";
        dashboardState.lastUpdate = nowStamp();
        setUploadLoading(true, "UPLINK_IN_PROGRESS");
        updateCounters();
        appendFeed(
            "INGEST",
            `${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"} accepted into intake chamber.`,
            uploadLabel,
        );

        const formData = new FormData();
        selectedFiles.forEach((file) => {
            formData.append("file", file);
        });

        try {
            const response = await window.blackTapeFetch("/upload", { method: "POST", body: formData });
            const result = await response.json();
            if (!response.ok || !result.job_id) {
                throw new Error(result.message || "Upload failed");
            }

            localStorage.setItem("blacktape_job_id", result.job_id);
            dashboardState.activeJobId = result.job_id;
            dashboardState.activeStatus = "PROCESSING";
            dashboardState.lastUpdate = nowStamp();
            setUploadLoading(true, "INDEXING_PAYLOAD");
            updateCounters();
            appendFeed(
                "PARSE",
                `${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"} entered background indexing.`,
                "Status polling engaged.",
            );
            await pollVaultStatus(uploadLabel, result.job_id);
        } catch (error) {
            console.error("Upload failed:", error);
            dashboardState.activeStatus = "FAULT";
            dashboardState.isUploading = false;
            setUploadLoading(false, "UPLOAD_FAULT_DETECTED");
            updateCounters();
            appendFeed("FAULT", `Upload failed for ${uploadLabel}.`, error.message);
        } finally {
            input.value = "";
        }
    };

    button.addEventListener("click", () => {
        input.value = "";
        input.click();
    });
    input.addEventListener("change", () => acceptFiles(input.files));
    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("is-dragover");
        });
    });
    ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("is-dragover");
        });
    });
    dropzone.addEventListener("drop", (event) => acceptFiles(event.dataTransfer.files));
}

async function bootstrapDashboard() {
    renderFeed();
    updateCounters();
    wireUpload();

    if (dashboardState.activeJobId) {
        dashboardState.activeStatus = "RELINK";
        dashboardState.lastUpdate = nowStamp();
        dashboardState.lastPolledStatus = "";
        updateCounters();
        await pollVaultStatus("active_vault", dashboardState.activeJobId);
    }
}

document.addEventListener("DOMContentLoaded", bootstrapDashboard);
