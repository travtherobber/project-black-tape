/**
 * Global System Module - Project Black-Tape
 * Handles core application logic, data ingestion, and persistent storage management.
 * STATUS: OPERATIONAL // SIGNAL_CLEAN
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log("[Module] Global System initialized.");

    const statusText = document.getElementById('status-indicator');
    if (statusText && !statusText.innerText.includes("OFFLINE")) {
        statusText.style.color = "var(--neon-green)";
    }
});

/**
 * Normalizes and converts UTC/ISO timestamps to the globally selected timezone.
 */
function convertToLocal(timestamp) {
    if (!timestamp || timestamp === "N/A" || timestamp === "1970-01-01 00:00:00 UTC") return "SIGNAL_TIME_UNKNOWN";

    // Clean timestamp for standard Date parsing
    let cleanTs = timestamp.replace(" UTC", "").replace(" ", "T");
    if (!cleanTs.includes("Z") && !/[+-]\d{2}:?\d{2}$/.test(cleanTs)) {
        cleanTs += "Z";
    }

    const date = new Date(cleanTs);
    if (isNaN(date.getTime())) return timestamp;

    const tz = localStorage.getItem('blacktape_timezone') || 'UTC';

    try {
        return new Intl.DateTimeFormat('en-US', {
            timeZone: tz,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false // 24hr format for industrial UI
        }).format(date).replace(/\//g, '-').replace(',', '');
    } catch (e) {
        console.error("Chrono conversion failure:", e);
        return timestamp;
    }
}

window.convertToLocal = convertToLocal;

/**
 * Appends a message to the system log display (Dashboard Terminal).
 */
function logToTerminal(message, type = 'INFO') {
    const feed = document.getElementById('system-log');
    if (!feed) return;

    const line = document.createElement('div');
    line.className = `stream-line type-${type.toLowerCase()}`;
    line.innerHTML = `> [ ${type} ] ${message}`;
    feed.appendChild(line);

    // Auto-scroll to keep the latest signal in view
    feed.scrollTop = feed.scrollHeight;
}

window.logToTerminal = logToTerminal;

/**
 * Handles file selection and transmission from the Dashboard.
 */
async function handleHomeUpload(input) {
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);

    const prompt = document.getElementById('ingestion-prompt');
    const btn = document.getElementById('upload-btn');
    const progressContainer = document.getElementById('upload-progress-container');
    const progressBar = document.getElementById('upload-progress-bar');
    const statusText = document.getElementById('upload-status-text');

    if (prompt) prompt.style.display = 'none';
    if (btn) btn.style.display = 'none';
    if (progressContainer) progressContainer.style.display = 'block';

    logToTerminal(`Initiating ingestion: ${file.name}`, "INFO");

    try {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                if (progressBar) progressBar.style.width = (percent * 0.4) + '%'; // Reserve 60% for backend processing
                if (statusText) statusText.innerText = `UPLOADING_SIGNAL_PACKETS: ${percent}%`;
            }
        };

        xhr.onload = async () => {
            if (xhr.status === 200 || xhr.status === 202) {
                const result = JSON.parse(xhr.responseText);
                // CRITICAL: This locks the signal ID into the browser
                localStorage.setItem('blacktape_job_id', result.job_id);
                logToTerminal(`Handshake verified. Job ID: ${result.job_id}`, "OK");
                startPolling(result.job_id);
            }
        };

        xhr.onerror = () => handleUploadError("Network connection severed.");
        xhr.send(formData);

    } catch (err) {
        handleUploadError(err.message);
    }
}

/**
 * Polls the status API with an explicit Job ID.
 */
function startPolling(jobId) {
    const progressBar = document.getElementById('upload-progress-bar');
    const statusText = document.getElementById('upload-status-text');

    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/vault/status?job_id=${jobId}`);
            const result = await response.json();

            if (result.status === "COMPLETE") {
                clearInterval(pollInterval);
                finalizeIngestion(jobId);
            } else if (result.status === "PROCESSING") {
                const msgCount = result.messages_found || 0;
                const gpsCount = result.gps_found || 0;

                if (statusText) {
                    statusText.innerText = `ALIGNING_SIGNALS: ${msgCount} MSGS // ${gpsCount} GPS`;
                }
                if (progressBar) progressBar.style.width = '75%';
            } else if (result.status === "ERROR" || result.status === "FAILED") {
                clearInterval(pollInterval);
                handleUploadError("Background processing failed.");
            }
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 1500); // Slightly faster polling for more responsive UI
}

/**
 * Finalizes using jobId and updates the UI visualization bars.
 */
async function finalizeIngestion(jobId) {
    const statusText = document.getElementById('upload-status-text');
    const progressBar = document.getElementById('upload-progress-bar');
    const prompt = document.getElementById('ingestion-prompt');
    const btn = document.getElementById('upload-btn');
    const progressContainer = document.getElementById('upload-progress-container');

    try {
        // Confirm the vault is actually ready to serve data
        const response = await fetch(`/api/conversations?job_id=${jobId}`);
        const result = await response.json();

        if (result.status === "SUCCESS" || result.status === "EMPTY") {
            localStorage.setItem('blacktape_active', 'true');

            if (progressBar) progressBar.style.width = '100%';
            if (statusText) {
                statusText.innerText = "ALIGNMENT_COMPLETE // READY";
                statusText.style.color = "var(--glow-mint)";
            }

            logToTerminal(`Signal alignment verified.`, "OK");
            updateDashboardBars(result.payload || []);

            // Reset UI after delay
            setTimeout(() => {
                if (progressContainer) progressContainer.style.display = 'none';
                if (btn) btn.style.display = 'block';
                if (prompt) {
                    prompt.style.display = 'block';
                    prompt.innerText = "SIGNAL_VAULT_RELOADED // STANDBY";
                }
            }, 3000);

        } else {
            handleUploadError("Vault verification failed.");
        }
    } catch (err) {
        handleUploadError(err.message);
    }
}

function handleUploadError(msg) {
    logToTerminal(`CRITICAL_FAULT: ${msg}`, "CRITICAL");
    const statusText = document.getElementById('upload-status-text');
    if (statusText) statusText.innerText = "FAULT: SIGNAL_REJECTED";

    document.getElementById('upload-btn').style.display = 'block';
    document.getElementById('ingestion-prompt').style.display = 'block';
}

/**
 * Animates the Dashboard visualizer bars based on data density.
 */
function updateDashboardBars(payload) {
    const chatBar = document.getElementById('bar-chats');
    const gpsBar = document.getElementById('bar-gps');
    const jobId = localStorage.getItem('blacktape_job_id');

    // Update Chat Bar height
    if (chatBar && payload.length > 0) {
        const height = Math.min(payload.length * 4, 100);
        chatBar.style.height = `${height}%`;
        logToTerminal(`Visualizing ${payload.length} chat clusters.`, "OK");
    }

    // Update GPS Bar height by pinging the GPS endpoint
    fetch(`/api/gps?job_id=${jobId}`)
        .then(res => res.json())
        .then(data => {
            if (gpsBar && data.payload && data.payload.length > 0) {
                const gpsHeight = Math.min(data.payload.length / 5, 100);
                gpsBar.style.height = `${gpsHeight}%`;
                logToTerminal(`Mapping ${data.payload.length} geospatial markers.`, "OK");
            }
        })
        .catch(err => console.error("GPS Sync Fault:", err));
}

async function purgeVault() {
    if (!confirm("Confirm complete vault purge? This cannot be undone.")) return;
    try {
        await fetch('/api/clear', { method: 'POST' });
        localStorage.removeItem('blacktape_job_id');
        localStorage.removeItem('blacktape_active');
        logToTerminal("Local vault purged.", "INFO");
        window.location.href = "/dashboard";
    } catch (err) {
        console.error("Purge failure:", err);
    }
}

window.handleHomeUpload = handleHomeUpload;
window.purgeVault = purgeVault;
