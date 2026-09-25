/* Local settings UI for Acute Midnight Pages. */
(async () => {
  "use strict";
  const storage = await browser.storage.local.get(["mode", "disabledHosts"]);
  const mode = ["off", "automatic", "always"].includes(storage.mode)
    ? storage.mode
    : "automatic";
  const disabledHosts = new Set(storage.disabledHosts || []);
  const selected = document.querySelector(`input[name="mode"][value="${mode}"]`);
  if (selected) selected.checked = true;

  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  let host = "";
  try {
    const url = new URL(tab.url);
    if (/^https?:$/.test(url.protocol)) host = url.hostname.toLowerCase();
  } catch (_) {
    // Internal and invalid URLs intentionally have no per-site control.
  }

  const reload = async () => {
    if (tab && Number.isInteger(tab.id)) await browser.tabs.reload(tab.id);
  };
  for (const input of document.querySelectorAll('input[name="mode"]')) {
    input.addEventListener("change", async () => {
      await browser.storage.local.set({ mode: input.value });
      await reload();
    });
  }

  if (host) {
    const controls = document.getElementById("site-controls");
    const siteName = document.getElementById("site-name");
    const siteEnabled = document.getElementById("site-enabled");
    controls.hidden = false;
    siteName.textContent = host;
    siteEnabled.checked = !disabledHosts.has(host);
    siteEnabled.addEventListener("change", async () => {
      if (siteEnabled.checked) disabledHosts.delete(host);
      else disabledHosts.add(host);
      await browser.storage.local.set({ disabledHosts: [...disabledHosts].sort() });
      await reload();
    });
  }
})();
