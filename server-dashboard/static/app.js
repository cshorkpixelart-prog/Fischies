"use strict";

const state = {
  role: document.body.dataset.role || "viewer",
  username: document.body.dataset.username || "",
  rods: [],
  selectedRodName: "",
  enchants: [],
  selectedEnchantName: "",
  feedback: [],
  selectedFeedbackId: "",
  channels: [],
  activeChannel: "",
  messages: [],
  users: [],
  autoRefreshTimer: null,
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
  "passiveInfo",
  "tutorialUrl",
  "notes",
];

const elements = {
  navLinks: document.querySelectorAll(".nav-link"),
  views: document.querySelectorAll(".view"),
  sumRods: document.getElementById("sum-rods"),
  sumEnchants: document.getElementById("sum-enchants"),
  sumFeedbackUnread: document.getElementById("sum-feedback-unread"),
  sumChannels: document.getElementById("sum-channels"),
  sumChatMessages: document.getElementById("sum-chat-messages"),
  activityList: document.getElementById("activity-list"),
  refreshActivity: document.getElementById("refresh-activity"),
  quickRefreshAll: document.getElementById("quick-refresh-all"),
  quickExportFeedback: document.getElementById("quick-export-feedback"),
  quickStatus: document.getElementById("quick-status"),
  rodTabs: document.getElementById("rod-tabs"),
  rodSearch: document.getElementById("rod-search"),
  rodForm: document.getElementById("rod-form"),
  rodFormTitle: document.getElementById("rod-form-title"),
  rodSaveStatus: document.getElementById("rod-save-status"),
  reloadRods: document.getElementById("reload-rods"),
  newRodName: document.getElementById("new-rod-name"),
  addRodBtn: document.getElementById("add-rod-btn"),
  toggleRodActiveBtn: document.getElementById("toggle-rod-active-btn"),
  rodAdminStatus: document.getElementById("rod-admin-status"),
  rodActivityState: document.getElementById("rod-activity-state"),
  tutorialFile: document.getElementById("field-tutorialFile"),
  uploadTutorialBtn: document.getElementById("upload-tutorial-btn"),
  tutorialUploadStatus: document.getElementById("tutorial-upload-status"),
  enchantTabs: document.getElementById("enchant-tabs"),
  enchantSearch: document.getElementById("enchant-search"),
  enchantForm: document.getElementById("enchant-form"),
  enchantFormTitle: document.getElementById("enchant-form-title"),
  enchantSaveStatus: document.getElementById("enchant-save-status"),
  reloadEnchants: document.getElementById("reload-enchants"),
  reloadFeedback: document.getElementById("reload-feedback"),
  feedbackSearch: document.getElementById("feedback-search"),
  feedbackShowArchived: document.getElementById("feedback-show-archived"),
  feedbackList: document.getElementById("feedback-list"),
  feedbackSubject: document.getElementById("feedback-subject"),
  feedbackMeta: document.getElementById("feedback-meta"),
  feedbackBody: document.getElementById("feedback-body"),
  feedbackToggleRead: document.getElementById("feedback-toggle-read"),
  feedbackToggleArchive: document.getElementById("feedback-toggle-archive"),
  channelList: document.getElementById("channel-list"),
  reloadChat: document.getElementById("reload-chat"),
  activeChannelTitle: document.getElementById("active-channel-title"),
  chatMessages: document.getElementById("chat-messages"),
  chatSendForm: document.getElementById("chat-send-form"),
  chatMessageInput: document.getElementById("chat-message-input"),
  channelCreateForm: document.getElementById("channel-create-form"),
  newChannelName: document.getElementById("new-channel-name"),
  newChannelTopic: document.getElementById("new-channel-topic"),
  usersNavLink: document.getElementById("users-nav-link"),
  userCreateForm: document.getElementById("user-create-form"),
  newUserName: document.getElementById("new-user-name"),
  newUserPass: document.getElementById("new-user-pass"),
  newUserRole: document.getElementById("new-user-role"),
  userList: document.getElementById("user-list"),
};

initialize();

function initialize() {
  bindNavigation();
  bindOverviewActions();
  bindRodActions();
  bindEnchantActions();
  bindFeedbackActions();
  bindChatActions();
  bindUserActions();
  applyRoleVisibility();
  refreshAll();
  startAutoRefresh();
}

function applyRoleVisibility() {
  const canManageChannels = state.role === "owner" || state.role === "admin";
  const canManageRods = state.role === "owner" || state.role === "admin";
  if (elements.channelCreateForm) {
    elements.channelCreateForm.classList.toggle("hidden", !canManageChannels);
  }
  if (elements.newRodName) {
    elements.newRodName.classList.toggle("hidden", !canManageRods);
  }
  if (elements.addRodBtn) {
    elements.addRodBtn.classList.toggle("hidden", !canManageRods);
  }
  if (elements.toggleRodActiveBtn) {
    elements.toggleRodActiveBtn.classList.toggle("hidden", !canManageRods);
  }
}

function bindNavigation() {
  elements.navLinks.forEach((link) => {
    link.addEventListener("click", () => {
      const target = link.dataset.view;
      if (!target) {
        return;
      }
      elements.navLinks.forEach((item) => item.classList.remove("active"));
      link.classList.add("active");
      elements.views.forEach((view) => view.classList.remove("active"));
      const selectedView = document.getElementById(`view-${target}`);
      if (selectedView) {
        selectedView.classList.add("active");
      }
    });
  });
}

function bindOverviewActions() {
  if (elements.refreshActivity) {
    elements.refreshActivity.addEventListener("click", loadActivity);
  }
  if (elements.quickRefreshAll) {
    elements.quickRefreshAll.addEventListener("click", async () => {
      elements.quickStatus.textContent = "Refreshing...";
      await refreshAll();
      elements.quickStatus.textContent = `Refreshed at ${formatDate(new Date().toISOString())}`;
    });
  }
  if (elements.quickExportFeedback) {
    elements.quickExportFeedback.addEventListener("click", () => {
      window.location.href = "/api/feedback/export";
    });
  }
}

function bindRodActions() {
  if (elements.rodSearch) {
    elements.rodSearch.addEventListener("input", () => {
      renderRodTabs(elements.rodSearch.value.trim().toLowerCase());
    });
  }
  if (elements.reloadRods) {
    elements.reloadRods.addEventListener("click", () => loadRods(true));
  }
  if (elements.rodForm) {
    elements.rodForm.addEventListener("submit", saveRodChanges);
  }
  if (elements.addRodBtn) {
    elements.addRodBtn.addEventListener("click", addRod);
  }
  if (elements.toggleRodActiveBtn) {
    elements.toggleRodActiveBtn.addEventListener("click", toggleRodActiveState);
  }
  if (elements.uploadTutorialBtn) {
    elements.uploadTutorialBtn.addEventListener("click", uploadTutorialVideo);
  }
}

function bindEnchantActions() {
  if (elements.enchantSearch) {
    elements.enchantSearch.addEventListener("input", () => {
      renderEnchantTabs(elements.enchantSearch.value.trim().toLowerCase());
    });
  }
  if (elements.reloadEnchants) {
    elements.reloadEnchants.addEventListener("click", () => loadEnchants(true));
  }
  if (elements.enchantForm) {
    elements.enchantForm.addEventListener("submit", saveEnchantChanges);
  }
}

function bindFeedbackActions() {
  if (elements.reloadFeedback) {
    elements.reloadFeedback.addEventListener("click", () => loadFeedback());
  }
  if (elements.feedbackSearch) {
    elements.feedbackSearch.addEventListener("input", debounce(() => loadFeedback(), 220));
  }
  if (elements.feedbackShowArchived) {
    elements.feedbackShowArchived.addEventListener("change", () => loadFeedback());
  }
  if (elements.feedbackToggleRead) {
    elements.feedbackToggleRead.addEventListener("click", toggleFeedbackRead);
  }
  if (elements.feedbackToggleArchive) {
    elements.feedbackToggleArchive.addEventListener("click", toggleFeedbackArchive);
  }
}

function bindChatActions() {
  if (elements.reloadChat) {
    elements.reloadChat.addEventListener("click", async () => {
      await loadChatChannels(false);
      await loadChatMessages();
    });
  }
  if (elements.chatSendForm) {
    elements.chatSendForm.addEventListener("submit", sendChatMessage);
  }
  if (elements.channelCreateForm) {
    elements.channelCreateForm.addEventListener("submit", createChannel);
  }
}

function bindUserActions() {
  if (elements.userCreateForm) {
    elements.userCreateForm.addEventListener("submit", createUser);
  }
}

function startAutoRefresh() {
  if (state.autoRefreshTimer) {
    clearInterval(state.autoRefreshTimer);
  }
  state.autoRefreshTimer = setInterval(async () => {
    await Promise.all([
      loadSummary(),
      loadActivity(),
      loadFeedback(false),
      loadChatMessages(false),
      loadEnchants(true),
    ]);
  }, 20000);
}

async function refreshAll() {
  await Promise.all([
    loadSummary(),
    loadRods(false),
    loadEnchants(false),
    loadFeedback(),
    loadChatChannels(true),
    loadActivity(),
  ]);
  if (state.role === "owner") {
    await loadUsers();
  }
}

async function loadSummary() {
  const response = await apiRequest("/api/dashboard/summary");
  if (!response.ok || !response.data?.summary) {
    return;
  }
  const summary = response.data.summary;
  elements.sumRods.textContent = String(summary.rodCount ?? 0);
  if (elements.sumEnchants) {
    elements.sumEnchants.textContent = String(summary.enchantCount ?? 0);
  }
  elements.sumFeedbackUnread.textContent = String(summary.feedbackUnread ?? 0);
  elements.sumChannels.textContent = String(summary.channelCount ?? 0);
  elements.sumChatMessages.textContent = String(summary.chatMessageCount ?? 0);
}

async function loadActivity() {
  const response = await apiRequest("/api/activity?limit=40");
  if (!response.ok || !Array.isArray(response.data?.activity)) {
    elements.activityList.innerHTML = "<p class='muted-text'>Could not load activity.</p>";
    return;
  }
  const fragment = document.createDocumentFragment();
  for (const entry of response.data.activity) {
    const item = document.createElement("article");
    item.className = "activity-item";
    const head = document.createElement("strong");
    head.textContent = `${entry.actor || "system"} · ${entry.type || "event"}`;
    const message = document.createElement("p");
    message.textContent = `${entry.message || ""} (${formatDate(entry.createdAt)})`;
    item.appendChild(head);
    item.appendChild(message);
    fragment.appendChild(item);
  }
  elements.activityList.innerHTML = "";
  elements.activityList.appendChild(fragment);
}

async function loadRods(keepSelection) {
  const response = await apiRequest("/api/rods?includeInactive=true");
  if (!response.ok || !Array.isArray(response.data?.rods)) {
    elements.rodTabs.innerHTML = "<p class='muted-text'>Could not load rods.</p>";
    return;
  }

  state.rods = response.data.rods.slice().sort((a, b) => String(a.name).localeCompare(String(b.name)));
  const defaultRodName = (state.rods.find((rod) => rod.active !== false) || state.rods[0] || {}).name || "";
  if (!keepSelection || !state.selectedRodName) {
    state.selectedRodName = defaultRodName;
  } else if (!state.rods.find((rod) => rod.name === state.selectedRodName)) {
    state.selectedRodName = defaultRodName;
  }
  renderRodTabs(elements.rodSearch.value.trim().toLowerCase());
  selectRod(state.selectedRodName);
}

function renderRodTabs(filterText) {
  elements.rodTabs.innerHTML = "";
  const visible = state.rods.filter(
    (rod) => !filterText || String(rod.name || "").toLowerCase().includes(filterText)
  );
  if (!visible.length) {
    elements.rodTabs.innerHTML = "<p class='muted-text'>No matching rods.</p>";
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const rod of visible) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rod-tab";
    if (rod.name === state.selectedRodName) {
      button.classList.add("active");
    }
    const isActive = rod.active !== false;
    button.textContent = isActive ? rod.name : `${rod.name} (inactive)`;
    if (!isActive) {
      button.classList.add("inactive");
    }
    button.addEventListener("click", () => selectRod(rod.name));
    fragment.appendChild(button);
  }
  elements.rodTabs.appendChild(fragment);
}

function selectRod(rodName) {
  const rod = state.rods.find((item) => item.name === rodName);
  state.selectedRodName = rod?.name || "";
  renderRodTabs(elements.rodSearch.value.trim().toLowerCase());

  if (!rod) {
    elements.rodFormTitle.textContent = "Select a rod";
    if (elements.rodActivityState) {
      elements.rodActivityState.textContent = "State: n/a";
    }
    if (elements.toggleRodActiveBtn) {
      elements.toggleRodActiveBtn.disabled = true;
      elements.toggleRodActiveBtn.textContent = "Deactivate Rod";
    }
    clearRodForm();
    return;
  }
  elements.rodFormTitle.textContent = rod.name;
  if (elements.rodActivityState) {
    elements.rodActivityState.textContent = `State: ${rod.active === false ? "inactive" : "active"}`;
  }
  if (elements.toggleRodActiveBtn) {
    const isActive = rod.active !== false;
    elements.toggleRodActiveBtn.disabled = false;
    elements.toggleRodActiveBtn.textContent = isActive ? "Deactivate Rod" : "Restore Rod";
  }
  fillRodForm(rod);
}

function fillRodForm(rod) {
  const stats = rod.stats || {};
  const catching = rod.catching || {};
  const learning = rod.learning || {};
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
  setField("passiveInfo", rod.passiveInfo || "");
  setField("tutorialUrl", rod.tutorialUrl || "");
  setField("notes", rod.notes || "");
  setRawField("field-learning-samples", learning.sampleCount ?? 0);
  const sampleCount = Number(learning.sampleCount || 0);
  const successCount = Number(learning.successCount || 0);
  const successRate = sampleCount > 0 ? ((successCount / sampleCount) * 100).toFixed(2) : "0.00";
  setRawField("field-learning-success-rate", `${successRate}%`);
  setRawField("field-learning-last-outcome", learning.lastOutcome || "none");
}

function clearRodForm() {
  for (const fieldId of fieldIds) {
    setField(fieldId, "");
  }
  setRawField("field-learning-samples", "");
  setRawField("field-learning-success-rate", "");
  setRawField("field-learning-last-outcome", "");
}

function setField(fieldId, value) {
  const element = document.getElementById(`field-${fieldId}`);
  if (!element) {
    return;
  }
  element.value = value === undefined || value === null ? "" : String(value);
}

function setRawField(elementId, value) {
  const element = document.getElementById(elementId);
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
    passiveInfo: document.getElementById("field-passiveInfo").value || "",
    tutorialUrl: document.getElementById("field-tutorialUrl").value || "",
    notes: document.getElementById("field-notes").value || "",
  };

  const encodedName = encodeURIComponent(state.selectedRodName);
  const response = await apiRequest(`/api/rods/${encodedName}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  elements.rodSaveStatus.textContent = response.ok ? "Saved." : "Save failed.";
  if (response.ok) {
    await loadRods(true);
    await loadSummary();
  }
}

async function addRod() {
  const rawName = String(elements.newRodName?.value || "").trim();
  if (!rawName) {
    if (elements.rodAdminStatus) {
      elements.rodAdminStatus.textContent = "Enter a rod name.";
    }
    return;
  }

  const response = await apiRequest("/api/rods", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: rawName }),
  });

  if (!response.ok || !response.data?.rod) {
    if (elements.rodAdminStatus) {
      elements.rodAdminStatus.textContent = response.data?.error || "Failed to add rod.";
    }
    return;
  }

  state.selectedRodName = response.data.rod.name;
  if (elements.newRodName) {
    elements.newRodName.value = "";
  }
  if (elements.rodAdminStatus) {
    elements.rodAdminStatus.textContent = "Rod created.";
  }
  await loadRods(true);
  await loadSummary();
}

async function toggleRodActiveState() {
  const rod = state.rods.find((item) => item.name === state.selectedRodName);
  if (!rod) {
    return;
  }

  const nextActive = rod.active === false;
  const response = await apiRequest(`/api/rods/${encodeURIComponent(rod.name)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active: nextActive }),
  });

  if (!response.ok) {
    if (elements.rodAdminStatus) {
      elements.rodAdminStatus.textContent = response.data?.error || "Failed to update rod state.";
    }
    return;
  }

  if (elements.rodAdminStatus) {
    elements.rodAdminStatus.textContent = nextActive ? "Rod restored." : "Rod deactivated.";
  }
  await loadRods(true);
  await loadSummary();
}

async function uploadTutorialVideo() {
  if (!state.selectedRodName) {
    return;
  }
  const file = elements.tutorialFile?.files?.[0];
  if (!file) {
    if (elements.tutorialUploadStatus) {
      elements.tutorialUploadStatus.textContent = "Choose a video file first.";
    }
    return;
  }

  if (elements.tutorialUploadStatus) {
    elements.tutorialUploadStatus.textContent = "Uploading...";
  }

  const payload = new FormData();
  payload.append("file", file);
  const response = await apiRequest("/api/tutorials/upload", {
    method: "POST",
    body: payload,
  });

  if (!response.ok || !response.data?.url) {
    if (elements.tutorialUploadStatus) {
      elements.tutorialUploadStatus.textContent = "Upload failed.";
    }
    return;
  }

  const tutorialField = document.getElementById("field-tutorialUrl");
  if (tutorialField) {
    tutorialField.value = String(response.data.url);
  }
  if (elements.tutorialFile) {
    elements.tutorialFile.value = "";
  }
  if (elements.tutorialUploadStatus) {
    elements.tutorialUploadStatus.textContent = "Upload complete. Save rod to persist.";
  }
}

async function loadEnchants(keepSelection) {
  if (!elements.enchantTabs) {
    return;
  }
  const response = await apiRequest("/api/enchants");
  if (!response.ok || !Array.isArray(response.data?.enchants)) {
    elements.enchantTabs.innerHTML = "<p class='muted-text'>Could not load enchants.</p>";
    return;
  }

  state.enchants = response.data.enchants
    .slice()
    .sort((a, b) => String(a.name).localeCompare(String(b.name)));

  if (!keepSelection || !state.selectedEnchantName) {
    state.selectedEnchantName = state.enchants[0]?.name || "";
  } else if (!state.enchants.find((enchant) => enchant.name === state.selectedEnchantName)) {
    state.selectedEnchantName = state.enchants[0]?.name || "";
  }

  renderEnchantTabs(elements.enchantSearch.value.trim().toLowerCase());
  selectEnchant(state.selectedEnchantName);
}

function renderEnchantTabs(filterText) {
  if (!elements.enchantTabs) {
    return;
  }
  elements.enchantTabs.innerHTML = "";
  const visible = state.enchants.filter(
    (enchant) => !filterText || String(enchant.name || "").toLowerCase().includes(filterText)
  );
  if (!visible.length) {
    elements.enchantTabs.innerHTML = "<p class='muted-text'>No matching enchants.</p>";
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const enchant of visible) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rod-tab";
    if (enchant.name === state.selectedEnchantName) {
      button.classList.add("active");
    }
    const tag = enchant.type === "secondary" ? "secondary" : "primary";
    button.textContent = `${enchant.name} (${tag})`;
    button.addEventListener("click", () => selectEnchant(enchant.name));
    fragment.appendChild(button);
  }
  elements.enchantTabs.appendChild(fragment);
}

function selectEnchant(enchantName) {
  const enchant = state.enchants.find((item) => item.name === enchantName);
  state.selectedEnchantName = enchant?.name || "";
  renderEnchantTabs(elements.enchantSearch.value.trim().toLowerCase());

  if (!enchant) {
    elements.enchantFormTitle.textContent = "Select an enchant";
    clearEnchantForm();
    return;
  }
  elements.enchantFormTitle.textContent = enchant.name;
  fillEnchantForm(enchant);
}

function fillEnchantForm(enchant) {
  const stats = enchant.stats || {};
  setEnchantField("name", enchant.name || "");
  setEnchantField("type", enchant.type || "primary");
  setEnchantField("effect", enchant.effect || "");
  setEnchantField("lure", stats.lure);
  setEnchantField("luck", stats.luck);
  setEnchantField("control", stats.control);
  setEnchantField("resilience", stats.resilience);
  setEnchantField("maxkg", stats.maxKg);
  setEnchantField("maxkgpercent", stats.maxKgPercent);
  setEnchantField("notes", enchant.notes || "");
}

function clearEnchantForm() {
  setEnchantField("name", "");
  setEnchantField("type", "primary");
  setEnchantField("effect", "");
  setEnchantField("lure", "");
  setEnchantField("luck", "");
  setEnchantField("control", "");
  setEnchantField("resilience", "");
  setEnchantField("maxkg", "");
  setEnchantField("maxkgpercent", "");
  setEnchantField("notes", "");
}

function setEnchantField(fieldId, value) {
  const element = document.getElementById(`field-enchant-${fieldId}`);
  if (!element) {
    return;
  }
  element.value = value === undefined || value === null ? "" : String(value);
}

async function saveEnchantChanges(event) {
  event.preventDefault();
  if (!elements.enchantForm) {
    return;
  }

  const requestedName = String(document.getElementById("field-enchant-name")?.value || "").trim();
  if (!requestedName) {
    elements.enchantSaveStatus.textContent = "Name is required.";
    return;
  }

  const payload = {
    name: requestedName,
    type: document.getElementById("field-enchant-type").value || "primary",
    effect: document.getElementById("field-enchant-effect").value || "",
    stats: {
      lure: parseNumberField("field-enchant-lure"),
      luck: parseNumberField("field-enchant-luck"),
      control: parseNumberField("field-enchant-control"),
      resilience: parseNumberField("field-enchant-resilience"),
      maxKg: parseMaxKgField("field-enchant-maxkg"),
      maxKgPercent: parseNumberField("field-enchant-maxkgpercent"),
    },
    notes: document.getElementById("field-enchant-notes").value || "",
  };

  const targetName = state.selectedEnchantName || requestedName;
  const response = await apiRequest(`/api/enchants/${encodeURIComponent(targetName)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  elements.enchantSaveStatus.textContent = response.ok ? "Saved." : "Save failed.";
  if (response.ok) {
    state.selectedEnchantName = response.data?.enchant?.name || requestedName;
    await loadEnchants(true);
    await loadSummary();
  }
}

function parseNumberField(id) {
  const raw = String(document.getElementById(id)?.value || "").trim();
  if (!raw) {
    return null;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseMaxKgField(id) {
  const raw = String(document.getElementById(id)?.value || "").trim();
  if (!raw) {
    return null;
  }
  if (raw.toLowerCase() === "inf") {
    return "inf";
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

async function loadFeedback(updatePreview = true) {
  const q = encodeURIComponent(elements.feedbackSearch.value.trim());
  const archived = elements.feedbackShowArchived.checked ? "true" : "false";
  const response = await apiRequest(`/api/feedback?archived=${archived}&q=${q}`);
  if (!response.ok || !Array.isArray(response.data?.feedback)) {
    elements.feedbackList.innerHTML = "<p class='muted-text'>Could not load inbox.</p>";
    return;
  }
  state.feedback = response.data.feedback;
  if (!state.feedback.find((item) => item.id === state.selectedFeedbackId)) {
    state.selectedFeedbackId = state.feedback[0]?.id || "";
  }
  renderFeedbackList();
  if (updatePreview) {
    setFeedbackPreview(state.selectedFeedbackId);
  }
  await loadSummary();
}

function renderFeedbackList() {
  elements.feedbackList.innerHTML = "";
  if (!state.feedback.length) {
    elements.feedbackList.innerHTML = "<p class='muted-text'>Inbox is empty.</p>";
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const entry of state.feedback) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mail-item";
    if (!entry.read) {
      button.classList.add("unread");
    }
    if (entry.id === state.selectedFeedbackId) {
      button.classList.add("active");
    }

    const subject = document.createElement("h4");
    subject.textContent = `${entry.type || "General"} · ${entry.rodName || "no rod"}`;
    const body = document.createElement("p");
    body.textContent = `${(entry.description || "").slice(0, 85)}${entry.description?.length > 85 ? "..." : ""}`;
    const meta = document.createElement("p");
    meta.textContent = formatDate(entry.createdAt);

    button.appendChild(subject);
    button.appendChild(body);
    button.appendChild(meta);
    button.addEventListener("click", () => setFeedbackPreview(entry.id));
    fragment.appendChild(button);
  }
  elements.feedbackList.appendChild(fragment);
}

async function setFeedbackPreview(feedbackId) {
  const entry = state.feedback.find((item) => item.id === feedbackId);
  if (!entry) {
    state.selectedFeedbackId = "";
    elements.feedbackSubject.textContent = "Select a message";
    elements.feedbackMeta.textContent = "";
    elements.feedbackBody.textContent = "Open a message from the inbox list to review details.";
    elements.feedbackToggleRead.disabled = true;
    elements.feedbackToggleArchive.disabled = true;
    return;
  }

  state.selectedFeedbackId = entry.id;
  renderFeedbackList();
  elements.feedbackSubject.textContent = `${entry.type || "General"} · ${entry.rodName || "No rod"}`;
  elements.feedbackMeta.textContent = `${formatDate(entry.createdAt)} · Client ${entry.clientTitle || "unknown"} ${entry.clientVersion || ""}`;
  elements.feedbackBody.textContent = entry.description || "";
  elements.feedbackToggleRead.disabled = false;
  elements.feedbackToggleArchive.disabled = false;
  elements.feedbackToggleRead.textContent = entry.read ? "Mark Unread" : "Mark Read";
  elements.feedbackToggleArchive.textContent = entry.archived ? "Restore" : "Archive";

  if (!entry.read) {
    await updateFeedbackState(entry.id, { read: true }, false);
  }
}

async function toggleFeedbackRead() {
  const entry = state.feedback.find((item) => item.id === state.selectedFeedbackId);
  if (!entry) {
    return;
  }
  await updateFeedbackState(entry.id, { read: !entry.read }, true);
}

async function toggleFeedbackArchive() {
  const entry = state.feedback.find((item) => item.id === state.selectedFeedbackId);
  if (!entry) {
    return;
  }
  await updateFeedbackState(entry.id, { archived: !entry.archived }, true);
}

async function updateFeedbackState(feedbackId, patch, refreshPreview) {
  const response = await apiRequest(`/api/feedback/${encodeURIComponent(feedbackId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!response.ok || !response.data?.feedback) {
    return;
  }
  const updated = response.data.feedback;
  state.feedback = state.feedback.map((entry) => (entry.id === updated.id ? updated : entry));
  renderFeedbackList();
  if (refreshPreview) {
    await setFeedbackPreview(updated.id);
  }
  await loadSummary();
}

async function loadChatChannels(selectDefault) {
  const response = await apiRequest("/api/chat/channels");
  if (!response.ok || !Array.isArray(response.data?.channels)) {
    elements.channelList.innerHTML = "<p class='muted-text'>Could not load channels.</p>";
    return;
  }
  state.channels = response.data.channels;
  if (!state.activeChannel || selectDefault) {
    state.activeChannel = state.channels[0]?.name || "";
  } else if (!state.channels.find((channel) => channel.name === state.activeChannel)) {
    state.activeChannel = state.channels[0]?.name || "";
  }
  renderChannels();
  await loadChatMessages(true);
  await loadSummary();
}

function renderChannels() {
  elements.channelList.innerHTML = "";
  const fragment = document.createDocumentFragment();
  for (const channel of state.channels) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "channel-btn";
    if (channel.name === state.activeChannel) {
      button.classList.add("active");
    }
    button.textContent = `# ${channel.name}`;
    button.title = channel.topic || "";
    button.addEventListener("click", async () => {
      state.activeChannel = channel.name;
      renderChannels();
      await loadChatMessages(true);
    });
    fragment.appendChild(button);
  }
  elements.channelList.appendChild(fragment);
}

async function loadChatMessages(scrollToBottom = false) {
  if (!state.activeChannel) {
    elements.chatMessages.innerHTML = "<p class='muted-text'>No channels available.</p>";
    return;
  }
  const query = encodeURIComponent(state.activeChannel);
  const response = await apiRequest(`/api/chat/messages?channel=${query}&limit=250`);
  if (!response.ok || !Array.isArray(response.data?.messages)) {
    elements.chatMessages.innerHTML = "<p class='muted-text'>Could not load messages.</p>";
    return;
  }
  state.messages = response.data.messages;
  elements.activeChannelTitle.textContent = `# ${state.activeChannel}`;
  renderMessages(scrollToBottom);
  await loadSummary();
}

function renderMessages(scrollToBottom) {
  elements.chatMessages.innerHTML = "";
  if (!state.messages.length) {
    elements.chatMessages.innerHTML = "<p class='muted-text'>No messages yet.</p>";
    return;
  }
  const fragment = document.createDocumentFragment();
  for (const message of state.messages) {
    const card = document.createElement("article");
    card.className = "chat-message";
    const meta = document.createElement("div");
    meta.className = "chat-message-meta";
    meta.textContent = `${message.author || "unknown"} · ${formatDate(message.createdAt)}`;
    const text = document.createElement("div");
    text.className = "chat-message-text";
    text.textContent = message.text || "";
    card.appendChild(meta);
    card.appendChild(text);
    fragment.appendChild(card);
  }
  elements.chatMessages.appendChild(fragment);
  if (scrollToBottom) {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  }
}

async function sendChatMessage(event) {
  event.preventDefault();
  const text = elements.chatMessageInput.value.trim();
  if (!text || !state.activeChannel) {
    return;
  }
  const response = await apiRequest("/api/chat/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel: state.activeChannel, text }),
  });
  if (!response.ok) {
    return;
  }
  elements.chatMessageInput.value = "";
  await loadChatMessages(true);
}

async function createChannel(event) {
  event.preventDefault();
  const name = elements.newChannelName.value.trim();
  const topic = elements.newChannelTopic.value.trim();
  if (!name) {
    return;
  }
  const response = await apiRequest("/api/chat/channels", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, topic }),
  });
  if (!response.ok) {
    return;
  }
  elements.newChannelName.value = "";
  elements.newChannelTopic.value = "";
  await loadChatChannels(false);
}

async function loadUsers() {
  if (state.role !== "owner") {
    return;
  }
  const response = await apiRequest("/api/users");
  if (!response.ok || !Array.isArray(response.data?.users)) {
    elements.userList.innerHTML = "<p class='muted-text'>Could not load users.</p>";
    return;
  }
  state.users = response.data.users;
  renderUsers();
  await loadSummary();
}

function renderUsers() {
  elements.userList.innerHTML = "";
  if (!state.users.length) {
    elements.userList.innerHTML = "<p class='muted-text'>No users found.</p>";
    return;
  }
  const fragment = document.createDocumentFragment();
  for (const user of state.users) {
    const wrapper = document.createElement("article");
    wrapper.className = "user-item";
    const info = document.createElement("div");
    const head = document.createElement("strong");
    head.textContent = `${user.username} (${user.role})`;
    const meta = document.createElement("p");
    meta.textContent = `Created ${formatDate(user.createdAt)} · Last login ${formatDate(user.lastLoginAt)}`;
    info.appendChild(head);
    info.appendChild(meta);

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "6px";
    const resetButton = document.createElement("button");
    resetButton.type = "button";
    resetButton.className = "ghost-btn";
    resetButton.textContent = "Reset Password";
    resetButton.addEventListener("click", () => promptResetPassword(user.username));
    actions.appendChild(resetButton);

    if (user.username !== "Makoral.Dev") {
      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "ghost-btn";
      deleteButton.textContent = "Delete";
      deleteButton.addEventListener("click", () => deleteUser(user.username));
      actions.appendChild(deleteButton);
    }

    wrapper.appendChild(info);
    wrapper.appendChild(actions);
    fragment.appendChild(wrapper);
  }
  elements.userList.appendChild(fragment);
}

async function createUser(event) {
  event.preventDefault();
  const username = elements.newUserName.value.trim();
  const password = elements.newUserPass.value;
  const role = elements.newUserRole.value;
  if (!username || !password) {
    return;
  }
  const response = await apiRequest("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, role }),
  });
  if (!response.ok) {
    alert(response.data?.error || "Failed to add user.");
    return;
  }
  elements.newUserName.value = "";
  elements.newUserPass.value = "";
  await loadUsers();
}

async function promptResetPassword(username) {
  const password = prompt(`Enter new password for ${username}:`);
  if (!password) {
    return;
  }
  const response = await apiRequest(`/api/users/${encodeURIComponent(username)}/password`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    alert(response.data?.error || "Could not reset password.");
    return;
  }
  alert(`Password updated for ${username}.`);
  if (response.data?.loggedOut) {
    window.location.href = "/login";
  }
}

async function deleteUser(username) {
  if (!confirm(`Delete user ${username}?`)) {
    return;
  }
  const response = await apiRequest(`/api/users/${encodeURIComponent(username)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    alert(response.data?.error || "Could not delete user.");
    return;
  }
  await loadUsers();
}

async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, options);
    if (response.status === 401) {
      window.location.href = "/login";
      return { ok: false, status: 401, data: null };
    }
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
    return "unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString();
}

function debounce(fn, wait) {
  let timeout = null;
  return (...args) => {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => fn(...args), wait);
  };
}
