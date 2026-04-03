function syncAppHeight() {
    document.documentElement.style.setProperty("--app-height", `${window.innerHeight}px`);
}

function initAbyssBackground() {
    const canvas = document.getElementById("abyss-canvas");
    if (!canvas) return;
    const shouldReduceEffects = window.matchMedia("(max-width: 720px)").matches
        || window.matchMedia("(prefers-reduced-motion: reduce)").matches
        || navigator.connection?.saveData;
    if (shouldReduceEffects) {
        canvas.hidden = true;
        return;
    }
    const context = canvas.getContext("2d");
    const particles = [];

    const resize = () => {
        canvas.width = window.innerWidth * window.devicePixelRatio;
        canvas.height = window.innerHeight * window.devicePixelRatio;
        context.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    };

    const seedParticles = () => {
        particles.length = 0;
        const count = Math.max(36, Math.floor((window.innerWidth * window.innerHeight) / 26000));
        for (let index = 0; index < count; index += 1) {
            particles.push({
                x: Math.random() * window.innerWidth,
                y: Math.random() * window.innerHeight,
                radius: Math.random() * 1.8 + 0.4,
                speedY: Math.random() * 0.18 + 0.04,
                speedX: (Math.random() - 0.5) * 0.08,
                alpha: Math.random() * 0.3 + 0.08,
            });
        }
    };

    const draw = () => {
        context.clearRect(0, 0, window.innerWidth, window.innerHeight);
        const gradient = context.createLinearGradient(0, 0, 0, window.innerHeight);
        gradient.addColorStop(0, "rgba(10, 39, 43, 0.04)");
        gradient.addColorStop(1, "rgba(2, 8, 10, 0.18)");
        context.fillStyle = gradient;
        context.fillRect(0, 0, window.innerWidth, window.innerHeight);

        particles.forEach((particle) => {
            particle.x += particle.speedX;
            particle.y += particle.speedY;
            if (particle.y > window.innerHeight + 10) {
                particle.y = -10;
                particle.x = Math.random() * window.innerWidth;
            }
            if (particle.x < -10) particle.x = window.innerWidth + 10;
            if (particle.x > window.innerWidth + 10) particle.x = -10;

            context.beginPath();
            context.fillStyle = `rgba(155, 215, 205, ${particle.alpha})`;
            context.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
            context.fill();
        });

        requestAnimationFrame(draw);
    };

    window.addEventListener("resize", () => {
        resize();
        seedParticles();
    });

    resize();
    seedParticles();
    draw();
}

function initGlobalReadouts() {
    const sessionNode = document.getElementById("session-readout");
    if (sessionNode) {
        sessionNode.textContent = "BT-" + Math.random().toString(36).slice(2, 6).toUpperCase() + "-ALPHA";
    }
}

let vaultRetentionTimer = null;

function formatCountdown(secondsRemaining) {
    if (secondsRemaining <= 0) {
        return "00:00";
    }
    const minutes = Math.floor(secondsRemaining / 60);
    const seconds = secondsRemaining % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function updateRetentionUi(statusPayload) {
    const labelNode = document.getElementById("vault-retention-label");
    const countdownNode = document.getElementById("vault-retention-countdown");
    const noteNode = document.getElementById("vault-retention-note");
    const resetButton = document.getElementById("vault-retention-reset");
    if (!labelNode || !countdownNode || !noteNode || !resetButton) return;

    const status = statusPayload?.status || "IDLE";
    const expiresAt = Number(statusPayload?.expires_at || 0);

    if (!expiresAt || status === "IDLE") {
        labelNode.textContent = "No active vault";
        countdownNode.textContent = "--:--";
        noteNode.textContent = "Uploaded data is removed automatically.";
        resetButton.disabled = true;
        return;
    }

    labelNode.textContent = status === "PROCESSING" ? "Processing vault" : "Active vault";
    noteNode.textContent = "Server cache will purge automatically when the timer ends.";
    resetButton.disabled = false;

    const secondsRemaining = Math.max(0, Math.floor(expiresAt - (Date.now() / 1000)));
    countdownNode.textContent = formatCountdown(secondsRemaining);
    if (secondsRemaining === 0) {
        labelNode.textContent = "Vault expired";
        noteNode.textContent = "Refresh or upload again to continue.";
        resetButton.disabled = true;
    }
}

async function fetchVaultRetentionStatus() {
    const labelNode = document.getElementById("vault-retention-label");
    if (!labelNode) return null;
    try {
        const response = await fetch("/api/vault/status");
        return await response.json();
    } catch (_error) {
        return null;
    }
}

function initVaultRetentionSidebar() {
    const resetButton = document.getElementById("vault-retention-reset");
    const labelNode = document.getElementById("vault-retention-label");
    if (!resetButton || !labelNode) return;

    const refresh = async () => {
        const payload = await fetchVaultRetentionStatus();
        updateRetentionUi(payload);
    };

    refresh();
    vaultRetentionTimer = window.setInterval(refresh, 1000);

    resetButton.addEventListener("click", async () => {
        resetButton.disabled = true;
        try {
            const response = await blackTapeFetch("/api/vault/reset-expiry", { method: "POST" });
            const payload = await response.json();
            if (response.ok && payload?.payload) {
                updateRetentionUi(payload.payload);
            } else {
                updateRetentionUi(await fetchVaultRetentionStatus());
            }
        } finally {
            window.setTimeout(async () => {
                updateRetentionUi(await fetchVaultRetentionStatus());
            }, 150);
        }
    });
}

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
}

async function blackTapeFetch(url, options = {}) {
    const nextOptions = { ...options };
    const method = (nextOptions.method || "GET").toUpperCase();
    const headers = new Headers(nextOptions.headers || {});

    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
        headers.set("X-CSRF-Token", getCsrfToken());
    }

    nextOptions.headers = headers;
    return fetch(url, nextOptions);
}

function getActiveTimezone() {
    return localStorage.getItem("blacktape_timezone") || "UTC";
}

function convertToLocal(timestamp) {
    if (!timestamp) return "";
    const normalized = String(timestamp).replace(" UTC", "Z").replace(" ", "T");
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return String(timestamp);

    const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: getActiveTimezone(),
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    }).formatToParts(date);

    const lookup = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return `${lookup.year}-${lookup.month}-${lookup.day} ${lookup.hour}:${lookup.minute}:${lookup.second}`;
}

function logToTerminal(message, level = "INFO") {
    const stateNode = document.getElementById("system-state") || document.getElementById("header-ingest-state");
    if (stateNode) {
        stateNode.textContent = `${level}: ${message}`;
    }
}

function updateGlobalTimezone(tz) {
    localStorage.setItem("blacktape_timezone", tz);
    window.dispatchEvent(new CustomEvent("timezoneChanged", { detail: { timezone: tz } }));
}

document.addEventListener("DOMContentLoaded", () => {
    syncAppHeight();
    initAbyssBackground();
    initGlobalReadouts();
    initVaultRetentionSidebar();
    requestAnimationFrame(() => document.body.classList.add("is-ready"));

    const timezoneSelect = document.getElementById("timezone-select");
    if (timezoneSelect) {
        timezoneSelect.value = getActiveTimezone();
        timezoneSelect.addEventListener("change", (event) => updateGlobalTimezone(event.target.value));
    }

    const purgeButton = document.getElementById("global-purge-button");
    if (purgeButton) {
        purgeButton.addEventListener("click", async () => {
            await blackTapeFetch("/api/clear", { method: "POST" });
            localStorage.removeItem("blacktape_job_id");
            localStorage.removeItem("blacktape_search_seed");
            window.location.href = "/dashboard";
        });
    }
});

window.addEventListener("resize", syncAppHeight);
window.convertToLocal = convertToLocal;
window.logToTerminal = logToTerminal;
window.updateGlobalTimezone = updateGlobalTimezone;
window.blackTapeFetch = blackTapeFetch;
