/* Behavioral tests for the shipped scripts, using mocked DOM and browser APIs. */
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const flush = () => new Promise((resolve) => setImmediate(resolve));

function panel(kind, options = {}) {
  const elements = [];
  class Element {
    constructor(tag = "div") {
      this.tag = tag;
      this.children = [];
      this.handlers = {};
      this.value = "";
      this.textContent = "";
      this.disabled = false;
      elements.push(this);
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(event, handler) { this.handlers[event] = handler; }
    setAttribute() {}
    fire(event) { return this.handlers[event]({ preventDefault() {} }); }
  }
  const ids = new Map();
  const get = (id) => {
    if (!ids.has(id)) ids.set(id, new Element());
    return ids.get(id);
  };
  const submit = new Element("button");
  const calls = { saved: [], opened: [] };
  let data = options.data || {};
  const tabs = options.tabs || [{ url: "https://example.com/page#section", title: "Example" }];
  const document = {
    getElementById: get,
    createElement: (tag) => new Element(tag),
    querySelector: () => submit,
    querySelectorAll: () => elements.filter((element) => element.tag === "button"),
  };
  const browser = {
    storage: { local: {
      get: () => options.read ? options.read() : Promise.resolve(data),
      set: async (value) => {
        if (options.failWrite) throw new Error("disk full");
        calls.saved.push(JSON.parse(JSON.stringify(value)));
        data = { ...data, ...value };
      },
    } },
    tabs: {
      query: async () => tabs,
      create: async (value) => {
        if (options.failOpen) throw new Error("tab unavailable");
        calls.opened.push(value);
      },
    },
  };
  const script = fs.readFileSync(path.join(__dirname, "..", "overlay", "assets",
    "extensions", `acute-${kind}`, "popup.js"), "utf8");
  vm.runInNewContext(script, { document, browser, URL, Date, Math, console });
  return { get, submit, calls, options,
    buttons: (label) => elements.filter((element) =>
      element.tag === "button" && element.textContent === label) };
}

test("sessions exclude private/internal tabs and cap snapshot size/name", async () => {
  const tabs = Array.from({ length: 130 }, (_, i) => ({ url: `https://example.com/${i}` }));
  tabs.unshift({ url: "https://private.test", incognito: true }, { url: "about:config" });
  const p = panel("sessions", { tabs });
  await flush();
  p.get("session-name").value = "a".repeat(100);
  await p.get("save-form").fire("submit");
  const saved = p.calls.saved[0].savedSessions[0];
  assert.equal(saved.name.length, 60);
  assert.equal(saved.tabs.length, 100);
  assert.equal(saved.tabs[0].url, "https://example.com/0");
});

test("sessions cannot overwrite storage while initial read is pending", async () => {
  let finishRead;
  const p = panel("sessions", { read: () => new Promise((resolve) => { finishRead = resolve; }) });
  await p.get("save-form").fire("submit");
  assert.equal(p.calls.saved.length, 0);
  assert.equal(p.submit.disabled, true);
  finishRead({ savedSessions: [] });
  await flush();
  assert.equal(p.submit.disabled, false);
});

test("sessions rollback failed writes and keep a retryable editor", async () => {
  const p = panel("sessions", { failWrite: true });
  await flush();
  p.get("session-name").value = "Research";
  await p.get("save-form").fire("submit");
  assert.equal(p.get("sessions").children.length, 0);
  assert.equal(p.get("session-name").value, "Research");
  assert.match(p.get("status").textContent, /Could not/);
  p.options.failWrite = false;
  await p.get("save-form").fire("submit");
  assert.equal(p.calls.saved[0].savedSessions.length, 1);
});

test("sessions repeated taps do not create duplicate snapshots", async () => {
  const p = panel("sessions");
  await flush();
  await Promise.all([p.get("save-form").fire("submit"), p.get("save-form").fire("submit")]);
  assert.equal(p.calls.saved.length, 1);
});

test("sessions sanitize malformed stored entries before restoring", async () => {
  const p = panel("sessions", { data: { savedSessions: [null, { tabs: [
    { url: "javascript:alert(1)" }, { url: "about:config" },
    { url: "https://example.com/valid" }, null,
  ] }] } });
  await flush();
  await p.buttons("Open")[0].fire("click");
  assert.equal(p.calls.opened.length, 1);
  assert.equal(p.calls.opened[0].url, "https://example.com/valid");
});

test("notes use canonical addresses and bound text", async () => {
  const p = panel("notes");
  await flush();
  p.get("note").value = "x".repeat(6000);
  await p.get("note-form").fire("submit");
  const note = p.calls.saved[0].pageNotes["https://example.com/page"];
  assert.equal(note.text.length, 5000);
  assert.equal(note.url, "https://example.com/page");
});

test("notes refuse private/internal-page creation", async () => {
  for (const tab of [{ url: "https://secret.test", incognito: true }, { url: "about:config" }]) {
    const p = panel("notes", { tabs: [tab] });
    await flush();
    p.get("note").value = "Do not store";
    await p.get("note-form").fire("submit");
    assert.equal(p.calls.saved.length, 0);
    assert.equal(p.get("note").disabled, true);
  }
});

test("notes failed saves keep editor text without reporting success", async () => {
  const p = panel("notes", { failWrite: true });
  await flush();
  p.get("note").value = "Unsaved draft";
  await p.get("note-form").fire("submit");
  assert.equal(p.get("note").value, "Unsaved draft");
  assert.equal(p.get("notes").children.length, 0);
  assert.match(p.get("status").textContent, /Could not/);
  assert.equal(p.submit.disabled, false);
});

test("failed initial reads keep mutation controls disabled", async () => {
  for (const kind of ["notes", "sessions"]) {
    const p = panel(kind, { read: () => Promise.reject(new Error("read failed")) });
    await flush();
    assert.equal(p.submit.disabled, true);
    assert.match(p.get("status").textContent, /Could not load/);
  }
});

test("notes failed deletion preserves the saved note and editor", async () => {
  const p = panel("notes", { failWrite: true, data: { pageNotes: { a: {
    url: "https://example.com/page", title: "Saved", text: "Keep this", updatedAt: 1,
  } } } });
  await flush();
  await p.buttons("Delete")[0].fire("click");
  assert.equal(p.get("note").value, "Keep this");
  assert.equal(p.get("notes").children.length, 1);
});
