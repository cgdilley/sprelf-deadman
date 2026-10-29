const CREDENTIALS_KEY = "deadman.credentials";
const LAST_CHECKIN_KEY = "deadman.lastCheckIn";

const loginView = document.getElementById("login-view");
const checkinView = document.getElementById("checkin-view");
const loginForm = document.getElementById("login-form");
const checkinButton = document.getElementById("checkin-button");
const logoutButton = document.getElementById("logout-button");
const currentUser = document.getElementById("current-user");
const lastCheckin = document.getElementById("last-checkin");
const statusText = document.getElementById("status");
const errorText = document.getElementById("error");

function getCredentials() {
    const raw = localStorage.getItem(CREDENTIALS_KEY);
    return raw ? JSON.parse(raw) : null;
}

function showError(message) {
    errorText.textContent = message;
    statusText.textContent = "";
}

function showStatus(message) {
    statusText.textContent = message;
    errorText.textContent = "";
}

function renderLastCheckin() {
    const stored = localStorage.getItem(LAST_CHECKIN_KEY);
    lastCheckin.textContent = stored ? new Date(stored).toLocaleString() : "Never";
}

function render() {
    const credentials = getCredentials();
    if (credentials) {
        currentUser.textContent = credentials.username;
        loginView.classList.add("hidden");
        checkinView.classList.remove("hidden");
        renderLastCheckin();
    } else {
        checkinView.classList.add("hidden");
        loginView.classList.remove("hidden");
    }
    showError("");
    showStatus("");
}

loginForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const username = document.getElementById("login-username").value.trim();
    const secret = document.getElementById("login-secret").value;
    if (!username || !secret) {
        return;
    }
    localStorage.setItem(CREDENTIALS_KEY, JSON.stringify({ username, secret }));
    loginForm.reset();
    render();
});

logoutButton.addEventListener("click", () => {
    localStorage.removeItem(CREDENTIALS_KEY);
    render();
});

checkinButton.addEventListener("click", async () => {
    const credentials = getCredentials();
    if (!credentials) {
        render();
        return;
    }

    checkinButton.disabled = true;
    showStatus("Checking in...");

    // The Lambda reads username and secret from the query string. The timestamp is
    // omitted so the server records the current UTC time (the Lambda treats any
    // supplied timestamp as UTC, which would be wrong for a browser's local time).
    const params = new URLSearchParams({
        username: credentials.username,
        secret: credentials.secret,
    });

    try {
        const response = await fetch(`${CHECKIN_API_URL}?${params.toString()}`, {
            method: "POST",
        });

        const body = await response.text();
        let data = {};
        try {
            data = JSON.parse(body);
        } catch (parseError) {
            // Non-JSON response; the raw body is shown below instead.
        }

        if (!response.ok) {
            showError([
                `Check-in failed: HTTP ${response.status} ${response.statusText}`.trim(),
                `Message: ${data.message || body || "(empty response body)"}`,
                `Request URL: ${CHECKIN_API_URL}`,
            ].join("\n"));
            return;
        }

        if (!data.timestamp) {
            showError([
                "Check-in failed: response did not contain a timestamp",
                `HTTP ${response.status}`,
                `Response body: ${body || "(empty)"}`,
            ].join("\n"));
            return;
        }

        localStorage.setItem(LAST_CHECKIN_KEY, data.timestamp);
        renderLastCheckin();
        showStatus(data.message || "Check-in recorded");
    } catch (networkError) {
        showError([
            `Check-in failed: ${networkError.name}: ${networkError.message}`,
            `Request URL: ${CHECKIN_API_URL}`,
            "The request never got a response. Common causes: no network connection, CORS blocking the request, or an incorrect API URL in config.js.",
        ].join("\n"));
    } finally {
        checkinButton.disabled = false;
    }
});

render();

if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("sw.js").catch((error) => {
            console.error("Service worker registration failed", error);
        });
    });
}
