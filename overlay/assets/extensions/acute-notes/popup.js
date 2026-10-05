/* Acute Page Notes — bounded local notes attached to canonical page addresses. */
(() => {
  "use strict";

  const MAX_NOTES = 500;
  const MAX_NOTE_LENGTH = 5000;
  const state = { currentPage: null, notes: {} };
  const editor = document.getElementById("note");
  const count = document.getElementById("count");
  const status = document.getElementById("status");
  const list = document.getElementById("notes");
  const emptyState = document.getElementById("empty-state");
  let ready = false;
  let busy = false;

  const updateControls = () => {
    document.querySelectorAll("button").forEach((button) => {
      button.disabled = !ready || busy;
    });
    document.querySelector('#note-form button[type="submit"]').disabled =
      !ready || busy || !state.currentPage;
    editor.disabled = !ready || busy || !state.currentPage;
  };

  const runAction = async (action) => {
    if (!ready || busy) return;
    busy = true;
    const previous = JSON.parse(JSON.stringify(state.notes));
    updateControls();
    try {
      await action();
    } catch (_) {
      state.notes = previous;
      renderRecent();
      setStatus("Could not complete this action. Saved notes were kept; please try again.");
    } finally {
      busy = false;
      updateControls();
    }
  };

  const canonicalPage = (tab) => {
    if (!tab || tab.incognito) return null;
    try {
      const url = new URL(tab.url);
      if (!["http:", "https:"].includes(url.protocol)) return null;
      url.hash = "";
      return { key: url.href, url: url.href, title: String(tab.title || url.hostname).slice(0, 200) };
    } catch (_) {
      return null;
    }
  };

  const setStatus = (message) => {
    status.textContent = message;
  };

  const persist = async () => {
    await browser.storage.local.set({ pageNotes: state.notes });
  };

  const renderRecent = () => {
    const notes = Object.values(state.notes).sort((a, b) => b.updatedAt - a.updatedAt).slice(0, 50);
    list.replaceChildren();
    emptyState.hidden = notes.length > 0;
    for (const saved of notes) {
      const item = document.createElement("li");
      item.className = "saved-note";
      const description = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = saved.title;
      const excerpt = document.createElement("small");
      excerpt.textContent = saved.text.replace(/\s+/g, " ").slice(0, 70);
      description.append(title, excerpt);

      const actions = document.createElement("div");
      actions.className = "actions";
      const openButton = document.createElement("button");
      openButton.type = "button";
      openButton.textContent = "Open";
      openButton.addEventListener("click", () => runAction(async () => {
        await browser.tabs.create({ url: saved.url });
      }));
      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.className = "delete";
      deleteButton.textContent = "Delete";
      deleteButton.setAttribute("aria-label", `Delete note for ${saved.title}`);
      deleteButton.addEventListener("click", () => runAction(async () => {
        delete state.notes[saved.key];
        await persist();
        if (state.currentPage && state.currentPage.key === saved.key) editor.value = "";
        updateCount();
        renderRecent();
        setStatus("Note deleted.");
      }));
      actions.append(openButton, deleteButton);
      item.append(description, actions);
      list.append(item);
    }
  };

  const updateCount = () => {
    count.textContent = `${editor.value.length} / ${MAX_NOTE_LENGTH}`;
  };
  editor.addEventListener("input", updateCount);

  document.getElementById("note-form").addEventListener("submit", (event) => {
    event.preventDefault();
    return runAction(async () => {
      if (!state.currentPage) return;
      const text = editor.value.trim().slice(0, MAX_NOTE_LENGTH);
      if (text) {
        state.notes[state.currentPage.key] = {
          ...state.currentPage,
          text,
          updatedAt: Date.now(),
        };
        const recent = Object.values(state.notes).sort((a, b) => b.updatedAt - a.updatedAt);
        state.notes = Object.fromEntries(recent.slice(0, MAX_NOTES).map((note) => [note.key, note]));
      } else {
        delete state.notes[state.currentPage.key];
      }
      await persist();
      setStatus(text ? "Note saved locally." : "Empty note removed.");
      renderRecent();
    });
  });

  updateControls();
  Promise.all([
    browser.tabs.query({ active: true, currentWindow: true }),
    browser.storage.local.get("pageNotes"),
  ]).then(([tabs, { pageNotes = {} }]) => {
    state.currentPage = canonicalPage(tabs[0]);
    const storedNotes = pageNotes && typeof pageNotes === "object" && !Array.isArray(pageNotes)
      ? Object.values(pageNotes)
      : [];
    const normalizedNotes = storedNotes
      .map((saved) => {
        const page = canonicalPage({
          url: saved?.url,
          title: saved?.title,
          incognito: false,
        });
        const text = String(saved?.text || "").trim().slice(0, MAX_NOTE_LENGTH);
        return page && text
          ? { ...page, text, updatedAt: Number(saved.updatedAt) || 0 }
          : null;
      })
      .filter(Boolean)
      .sort((a, b) => b.updatedAt - a.updatedAt)
      .slice(0, MAX_NOTES);
    state.notes = Object.fromEntries(normalizedNotes.map((note) => [note.key, note]));
    if (!state.currentPage) {
      editor.disabled = true;
      document.querySelector('#note-form button[type="submit"]').disabled = true;
      document.getElementById("page-title").textContent = "Notes are unavailable for private or internal pages.";
    } else {
      document.getElementById("page-title").textContent = state.currentPage.title;
      editor.value = state.notes[state.currentPage.key]?.text || "";
    }
    updateCount();
    renderRecent();
    ready = true;
    updateControls();
  }).catch(() => {
    setStatus("Could not load page notes. Close this panel and try again; nothing was changed.");
  });
})();
