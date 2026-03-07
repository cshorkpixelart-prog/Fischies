"use strict";

const state = {
  rods: [],
  feedback: [],
  selectedRodName: "",
};

const THEME_STORAGE_KEY = "fisch-dashboard-theme";

const elements = {
  serverStatus: document.getElementById("server-status"),
  rodCount: document.getElementById("rod-count"),
  feedbackCount: document.getElementById("feedback-count"),
  lastRefresh: document.getElementById("last-refresh"),
  rodTabs: document.getElementById("rod-tabs"),
  rodSearch: document.getElementById("rod-search"),
  rodForm: document.getElementById("rod-form"),
  rodFormTitle: document.getElementById("rod-form-title"),
  rodSaveStatus: document.getElementById("rod-save-status"),
  feedbackList: document.getElementById("feedback-list"),
  reloadRods: document.getElementById("reload-rods"),
  reloadFeedback: document.getElementById("reload-feedback"),
  themeToggle: document.getElementById("theme-toggle"),
};

const fieldIds = [
  "lure",
  "luck",
  "control",
  "resilience",
  "maxkg",
  "centerRatio",
  "lookaheadMs",
  "brakeSpeed",
  "deadzonePx",
  "fishVelocitySmoothing",
  "barVelocitySmoothing",
  "notes",
];

initialize();

function initialize() {
  applyStoredTheme();
  bindEvents();
  loadAllData();
}

function bindEvents() {
  document.querySelectorAll(".nav-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.target;
      const section = document.getElementById(target);
      if (section) {
        section.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

  elements.rodSearch.addEventListener("input", () => {
    renderRodTabs(elements.rodSearch.value.trim().toLowerCase());
  });

  elements.reloadRods.addEventListener("click", () => loadRods(true));
  elements.reloadFeedback.addEventListener("click", loadFeedback);
  elements.rodForm.addEventListener("submit", saveRodChanges);

  if (elements.themeToggle) {
    elements.themeToggle.addEventListener("click", toggleTheme);
  }
}

async function loadAllData() {
  await Promise.all([loadHealth(), loadRods(false), loadFeedback()]);
  elements.lastRefresh.textContent = formatDate(new Date().toISOString());
}

async function loadHealth() {
  const response = await apiRequest("/api/health");
  if (!response.ok) {
    elements.serverStatus.textContent = "Server offline";
    return;
  }
  elements.serverStatus.textContent = "Server online";
}

async function loadRods(keepSelection) {
  const response = await apiRequest("/api/rods");
  if (!response.ok || !response.data || !Array.isArray(response.data.rods)) {
    elements.rodTabs.innerHTML = "<p>Could not load rod data.</p>";
    elements.rodCount.textContent = "-";
    return;
  }

  state.rods = response.data.rods.slice().sort((a, b) => a.name.localeCompare(b.name));
  elements.rodCount.textContent = String(state.rods.length);

  if (!keepSelection || !state.selectedRodName) {
    state.selectedRodName = state.rods.length ? state.rods[0].name : "";
  } else if (!state.rods.find((rod) => rod.name === state.selectedRodName)) {
    state.selectedRodName = state.rods.length ? state.rods[0].name : "";
  }

  renderRodTabs(elements.rodSearch.value.trim().toLowerCase());
  selectRod(state.selectedRodName);
  elements.lastRefresh.textContent = formatDate(new Date().toISOString());
}

function renderRodTabs(filterText) {
  elements.rodTabs.innerHTML = "";
  const fragment = document.createDocumentFragment();
  const visibleRods = state.rods.filter((rod) =>
    !filterText || rod.name.toLowerCase().includes(filterText)
  );

  for (const rod of visibleRods) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rod-tab";
    if (rod.name === state.selectedRodName) {
      button.classList.add("active");
    }
    button.textContent = rod.name;
    button.addEventListener("click", () => selectRod(rod.name));
    fragment.appendChild(button);
  }

  if (!visibleRods.length) {
    const message = document.createElement("p");
    message.textContent = "No matching rods.";
    fragment.appendChild(message);
  }

  elements.rodTabs.appendChild(fragment);
}

function selectRod(rodName) {
  const rod = state.rods.find((item) => item.name === rodName);
  state.selectedRodName = rod ? rod.name : "";
  renderRodTabs(elements.rodSearch.value.trim().toLowerCase());

  if (!rod) {
    elements.rodFormTitle.textContent = "Select a rod";
    clearForm();
    return;
  }

  elements.rodFormTitle.textContent = rod.name;
  fillFormFromRod(rod);
}

function fillFormFromRod(rod) {
  const stats = rod.stats || {};
  const catching = rod.catching || {};

  setField("lure", stats.lure);
  setField("luck", stats.luck);
  setField("control", stats.control);
  setField("resilience", stats.resilience);
  setField("maxkg", stats.maxKg);
  setField("centerRatio", catching.centerRatio);
  setField("lookaheadMs", catching.lookaheadMs);
  setField("brakeSpeed", catching.brakeSpeed);
  setField("deadzonePx", catching.deadzonePx);
  setField("fishVelocitySmoothing", catching.fishVelocitySmoothing);
  setField("barVelocitySmoothing", catching.barVelocitySmoothing);
  setField("notes", rod.notes || "");
}

function clearForm() {
  for (const fieldId of fieldIds) {
    setField(fieldId, "");
  }
}

function setField(fieldId, value) {
  const element = document.getElementById(`field-${fieldId}`);
  if (!element) {
    return;
  }
  element.value = value === undefined || value === null ? "" : String(value);
}

async function saveRodChanges(event) {
  event.preventDefault();
  if (!state.selectedRodName) {
    return;
  }

  const payload = {
    stats: {
      lure: parseNumberField("field-lure"),
      luck: parseNumberField("field-luck"),
      control: parseNumberField("field-control"),
      resilience: parseNumberField("field-resilience"),
      maxKg: parseMaxKgField("field-maxkg"),
    },
    catching: {
      centerRatio: parseNumberField("field-centerRatio"),
      lookaheadMs: parseNumberField("field-lookaheadMs"),
      brakeSpeed: parseNumberField("field-brakeSpeed"),
      deadzonePx: parseNumberField("field-deadzonePx"),
      fishVelocitySmoothing: parseNumberField("field-fishVelocitySmoothing"),
      barVelocitySmoothing: parseNumberField("field-barVelocitySmoothing"),
    },
    notes: document.getElementById("field-notes").value || "",
  };

  const encodedName = encodeURIComponent(state.selectedRodName);
  const response = await apiRequest(`/api/rods/${encodedName}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    elements.rodSaveStatus.textContent = "Save failed.";
    return;
  }

  elements.rodSaveStatus.textContent = "Saved.";
  await loadRods(true);
}

function parseNumberField(id) {
  const raw = document.getElementById(id).value.trim();
  if (!raw) {
    return null;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseMaxKgField(id) {
  const raw = document.getElementById(id).value.trim();
  if (!raw) {
    return null;
  }
  if (raw.toLowerCase() === "inf") {
    return "inf";
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

async function loadFeedback() {
  const response = await apiRequest("/api/feedback");
  if (!response.ok || !response.data || !Array.isArray(response.data.feedback)) {
    elements.feedbackList.innerHTML = "<p>Could not load feedback.</p>";
    elements.feedbackCount.textContent = "-";
    return;
  }

  state.feedback = response.data.feedback;
  elements.feedbackCount.textContent = String(state.feedback.length);
  renderFeedback();
  elements.lastRefresh.textContent = formatDate(new Date().toISOString());
}

function renderFeedback() {
  elements.feedbackList.innerHTML = "";
  if (!state.feedback.length) {
    elements.feedbackList.innerHTML = "<p>No feedback messages yet.</p>";
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const entry of state.feedback) {
    const wrapper = document.createElement("article");
    wrapper.className = "feedback-item";

    const top = document.createElement("div");
    top.className = "feedback-top";

    const type = document.createElement("span");
    type.className = "feedback-type";
    type.textContent = entry.type || "General";

    const meta = document.createElement("span");
    meta.className = "feedback-meta";
    meta.textContent = `${formatDate(entry.createdAt)} | Rod: ${entry.rodName || "n/a"}`;

    top.appendChild(type);
    top.appendChild(meta);

    const message = document.createElement("p");
    message.className = "feedback-body";
    message.textContent = entry.description || "";

    wrapper.appendChild(top);
    wrapper.appendChild(message);
    fragment.appendChild(wrapper);
  }

  elements.feedbackList.appendChild(fragment);
}

async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, options);
    const contentType = String(response.headers.get("content-type") || "").toLowerCase();
    let data = null;

    if (contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    return { ok: response.ok, status: response.status, data };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

function formatDate(value) {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString();
}

function applyStoredTheme() {
  let theme = null;
  try {
    theme = localStorage.getItem(THEME_STORAGE_KEY);
  } catch {
    theme = null;
  }

  if (theme !== "light" && theme !== "dark") {
    theme = "dark";
  }

  setTheme(theme, false);
}

function toggleTheme() {
  const currentTheme = document.documentElement.dataset.theme === "light" ? "light" : "dark";
  const nextTheme = currentTheme === "dark" ? "light" : "dark";
  setTheme(nextTheme, true);
}

function setTheme(theme, persist) {
  const nextTheme = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = nextTheme;

  if (elements.themeToggle) {
    const isDark = nextTheme === "dark";
    elements.themeToggle.textContent = isDark ? "Light mode" : "Dark mode";
    elements.themeToggle.title = isDark ? "Switch to light mode" : "Switch to dark mode";
    elements.themeToggle.setAttribute("aria-pressed", String(isDark));
  }

  if (!persist) {
    return;
  }

  try {
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
  } catch {
    // Ignore storage failures (private browsing or blocked storage).
  }
}
