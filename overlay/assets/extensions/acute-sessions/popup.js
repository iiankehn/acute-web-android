/* Acute Saved Sessions — local window snapshots without sync or accounts. */
(() => {
  "use strict";

  const MAX_SESSIONS = 50;
  const MAX_TABS_PER_SESSION = 100;
  const state = { sessions: [] };
  const list = document.getElementById("sessions");
  const emptyState = document.getElementById("empty-state");
  const status = document.getElementById("status");
  const nameInput = document.getElementById("session-name");
  let ready = false;
  let busy = false;

  const updateControls = () => {
    document.querySelectorAll("button").forEach((button) => {
      button.disabled = !ready || busy;
    });
  };

  const runAction = async (action) => {
    if (!ready || busy) return;
    busy = true;
    const previous = JSON.parse(JSON.stringify(state.sessions));
    updateControls();
    try {
      await action();
    } catch (_) {
      state.sessions = previous;
      render();
      setStatus("Could not complete this action. Saved sessions were kept; please try again.");
    } finally {
      busy = false;
      updateControls();
    }
  };

  const isWebAddress = (value) => {
    try {
      return ["http:", "https:"].includes(new URL(value).protocol);
    } catch (_) {
      return false;
    }
  };

  const store = async () => {
    await browser.storage.local.set({ savedSessions: state.sessions });
  };

  const setStatus = (message) => {
    status.textContent = message;
  };

  const render = () => {
    list.replaceChildren();
    emptyState.hidden = state.sessions.length > 0;
    for (const session of state.sessions) {
      const item = document.createElement("li");
      item.className = "session";

      const description = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = session.name;
      const detail = document.createElement("small");
      detail.textContent = `${session.tabs.length} ${session.tabs.length === 1 ? "tab" : "tabs"}`;
      description.append(title, detail);

      const actions = document.createElement("div");
      actions.className = "actions";
      const openButton = document.createElement("button");
      openButton.type = "button";
      openButton.textContent = "Open";
      openButton.addEventListener("click", () => runAction(async () => {
        const tabs = session.tabs.filter((tab) => isWebAddress(tab.url));
        for (const [index, tab] of tabs.entries()) {
          await browser.tabs.create({ url: tab.url, active: index === 0 });
        }
        setStatus(`Opened ${tabs.length} ${tabs.length === 1 ? "tab" : "tabs"}.`);
      }));
      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "delete";
      deleteButton.textContent = "Delete";
      deleteButton.setAttribute("aria-label", `Delete ${session.name}`);
      deleteButton.addEventListener("click", () => runAction(async () => {
        state.sessions = state.sessions.filter((candidate) => candidate.id !== session.id);
        await store();
        render();
        setStatus("Session deleted.");
      }));
      actions.append(openButton, deleteButton);
      item.append(description, actions);
      list.append(item);
    }
  };

  document.getElementById("save-form").addEventListener("submit", (event) => {
    event.preventDefault();
    return runAction(async () => {
      const currentTabs = await browser.tabs.query({ currentWindow: true });
      const tabs = currentTabs
        .filter((tab) => !tab.incognito && isWebAddress(tab.url))
        .slice(0, MAX_TABS_PER_SESSION)
        .map((tab) => ({ title: tab.title || tab.url, url: tab.url }));
      if (tabs.length === 0) {
        setStatus("There are no normal web tabs to save in this window.");
        return;
      }
      const fallbackName = `Session ${new Date().toLocaleDateString()}`;
      const name = (nameInput.value.trim() || fallbackName).slice(0, 60);
      state.sessions.unshift({
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        name,
        createdAt: Date.now(),
        tabs,
      });
      state.sessions = state.sessions.slice(0, MAX_SESSIONS);
      await store();
      nameInput.value = "";
      render();
      setStatus(`Saved ${tabs.length} ${tabs.length === 1 ? "tab" : "tabs"}.`);
    });
  });

  updateControls();
  browser.storage.local.get("savedSessions").then(({ savedSessions = [] }) => {
    state.sessions = Array.isArray(savedSessions)
      ? savedSessions
          .filter((session) => session && Array.isArray(session.tabs))
          .slice(0, MAX_SESSIONS)
          .map((session) => ({
            id: String(session.id || `${Date.now()}-${Math.random().toString(16).slice(2)}`),
            name: String(session.name || "Saved session").slice(0, 60),
            createdAt: Number(session.createdAt) || 0,
            tabs: session.tabs
              .filter((tab) => tab && isWebAddress(tab.url))
              .slice(0, MAX_TABS_PER_SESSION)
              .map((tab) => ({ title: String(tab.title || tab.url), url: tab.url })),
          }))
          .filter((session) => session.tabs.length > 0)
      : [];
    render();
    ready = true;
    updateControls();
  }).catch(() => {
    setStatus("Could not load saved sessions. Close this panel and try again; nothing was changed.");
  });
})();
