// Shared code for every page: talking to the two services, remembering the login,
// the menu, and showing messages. config.js (loaded first) says where the services are.

const TIMEOUT_MS = 5000; // never wait longer than 5 seconds for a service

// ---------- Login token (kept in this browser only) ----------
function getToken() { return localStorage.getItem("token"); }
function getUserName() { return localStorage.getItem("userName"); }
function saveLogin(body) {
    localStorage.setItem("token", body.token);
    localStorage.setItem("userName", body.user.name);
}
function logOut() {
    localStorage.removeItem("token");
    localStorage.removeItem("userName");
    window.location.href = "index.html";
}

// ---------- Calling a service ----------
// service is "bookings" or "restaurants". Returns { ok, status, body }.
// If the service can't be reached in time, status is 0 instead of throwing an error.
async function callService(service, path, options = {}) {
    const baseUrl = service === "bookings" ? window.CONFIG.BOOKINGS_URL : window.CONFIG.RESTAURANTS_URL;
    const headers = {};
    if (options.body) headers["Content-Type"] = "application/json";
    // Only Bookings needs to know who is logged in, so the token is never sent to Restaurants.
    if (service === "bookings" && getToken()) headers["Authorization"] = "Bearer " + getToken();

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    try {
        const response = await fetch(baseUrl + path, {
            method: options.method || "GET",
            headers: headers,
            body: options.body ? JSON.stringify(options.body) : undefined,
            signal: controller.signal,
        });
        const body = await response.json().catch(() => ({}));
        if (response.status === 401 && getToken()) logOut(); // token expired or invalid
        return { ok: response.ok, status: response.status, body: body };
    } catch (error) {
        return { ok: false, status: 0, body: {} };
    } finally {
        clearTimeout(timer);
    }
}

// Turns a failed answer into a list of messages a person can read.
function errorMessages(result) {
    if (result.status === 0) return ["We can't reach our servers right now. Please try again in a few minutes."];
    if (result.body.errors) return result.body.errors;
    if (result.body.message) return [result.body.message];
    return ["Something went wrong. Please try again."];
}

// ---------- Showing things on the page ----------
// Makes text safe to put inside HTML (so a name like "<b>" is shown, not run).
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text === null || text === undefined ? "" : String(text);
    return div.innerHTML;
}

function showErrors(messages) {
    const box = document.getElementById("errors");
    box.innerHTML = messages.map((m) => "<li>" + escapeHtml(m) + "</li>").join("");
    box.hidden = messages.length === 0;
}

function showFlash(message) {
    const box = document.getElementById("flash");
    box.textContent = message;
    box.hidden = !message;
}

// A flash message that survives going to another page (e.g. "Your dinner is booked").
function flashNextPage(message) { sessionStorage.setItem("flash", message); }
function showSavedFlash() {
    const message = sessionStorage.getItem("flash");
    sessionStorage.removeItem("flash");
    if (message) showFlash(message);
}

function themeName(theme) { return theme.replace("_", " "); }

// "2026-11-25T20:00:00" -> "Wednesday 25 November 2026 at 20:00"
function formatDate(isoText, withWeekday = true) {
    const date = new Date(isoText);
    const day = date.toLocaleDateString("en-GB", withWeekday
        ? { weekday: "long", day: "numeric", month: "long", year: "numeric" }
        : { day: "numeric", month: "short", year: "numeric" });
    const time = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    return day + " at " + time;
}

function stars(rating) { return "★".repeat(rating) + "☆".repeat(5 - rating); }

// ---------- Menu ----------
function renderNav() {
    const nav = document.getElementById("nav");
    let html = '<a href="cities.html">Cities</a>';
    if (getToken()) {
        html += '<a href="book.html">Book a dinner</a>' +
                '<a href="dinners.html">My dinners</a>' +
                '<button type="button" id="logout">Log out (' + escapeHtml(getUserName()) + ")</button>";
    } else {
        html += '<a href="signup.html">Sign up</a><a href="login.html">Log in</a>';
    }
    nav.innerHTML = html;
    const button = document.getElementById("logout");
    if (button) button.addEventListener("click", logOut);
}

// Pages that need a login send you to the login page first.
function requireLogin() {
    if (!getToken()) window.location.href = "login.html";
}

renderNav();
showSavedFlash();
