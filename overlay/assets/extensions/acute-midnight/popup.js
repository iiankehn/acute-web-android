/* Local settings UI for Acute Midnight Pages. */
(async () => {
  "use strict";
  const status = document.getElementById("status");
  const fieldset = document.querySelector("fieldset");
  const siteEnabled = document.getElementById("site-enabled");
  const inputs = [...document.querySelectorAll('input[name="mode"]')];
  let busy = false;
  const setBusy = (value) => {
    busy = value;
    fieldset.disabled = value;
    siteEnabled.disabled = value;
  };
  setBusy(true);
  try {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    if (browser.extension.inIncognitoContext || tab?.incognito) {
      status.textContent = "Midnight Pages is unavailable in private browsing.";
      return;
    }
    const storage = await browser.storage.local.get(["mode", "disabledHosts"]);
    let mode = ["off", "automatic", "always"].includes(storage.mode) ? storage.mode : "automatic";
    let disabledHosts = new Set(Array.isArray(storage.disabledHosts)
      ? storage.disabledHosts.filter((host) => typeof host === "string") : []);
    let host = "";
    const restoreControls = () => {
      for (const input of inputs) input.checked = input.value === mode;
      siteEnabled.checked = !disabledHosts.has(host);
    };
    try {
      const url = new URL(tab?.url);
      if (/^https?:$/.test(url.protocol)) host = url.hostname.toLowerCase();
    } catch (_) {
      // Internal and invalid URLs intentionally have no per-site control.
    }
    const save = async (values, commit) => {
      if (busy) { restoreControls(); return; }
      setBusy(true);
      status.textContent = "";
      try {
        await browser.storage.local.set(values);
        commit();
      } catch (_) {
        status.textContent = "Settings could not be saved. Please try again.";
        return;
      } finally {
        restoreControls();
        setBusy(false);
      }
      if (tab && Number.isInteger(tab.id)) {
        try { await browser.tabs.reload(tab.id); }
        catch (_) { status.textContent = "Settings saved. Reload the page to apply them."; }
      }
    };
    for (const input of inputs) {
      input.addEventListener("change", () => {
        const nextMode = input.value;
        return save({ mode: nextMode }, () => { mode = nextMode; });
      });
    }
    if (host) {
      document.getElementById("site-controls").hidden = false;
      document.getElementById("site-name").textContent = host;
      siteEnabled.addEventListener("change", () => {
        const next = new Set(disabledHosts);
        if (siteEnabled.checked) next.delete(host);
        else next.add(host);
        return save({ disabledHosts: [...next].sort() }, () => { disabledHosts = next; });
      });
    }
    restoreControls();
    setBusy(false);
  } catch (_) {
    status.textContent = "Settings could not be loaded. Close this panel and try again.";
  }
})();
