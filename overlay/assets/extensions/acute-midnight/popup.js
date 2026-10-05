/* Local settings UI for Acute Site Display. */
(async () => {
  "use strict";
  const storage = await browser.storage.local.get([
    "mode",
    "disabledHosts",
    "siteModes",
    "siteTextScales",
    "reducedMotionHosts",
  ]);
  const mode = ["off", "automatic", "always"].includes(storage.mode)
    ? storage.mode
    : "automatic";
  const disabledHosts = new Set(storage.disabledHosts || []);
  const siteModes = { ...(storage.siteModes || {}) };
  const siteTextScales = { ...(storage.siteTextScales || {}) };
  const reducedMotionHosts = new Set(storage.reducedMotionHosts || []);
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
    const siteAppearance = document.getElementById("site-appearance");
    const siteTextScale = document.getElementById("site-text-scale");
    const siteReduceMotion = document.getElementById("site-reduce-motion");
    controls.hidden = false;
    siteName.textContent = host;

    // Migrate the original enabled/disabled host model without losing choices.
    siteAppearance.value = siteModes[host] || (disabledHosts.has(host) ? "original" : "inherit");
    siteTextScale.value = String(siteTextScales[host] || 100);
    siteReduceMotion.checked = reducedMotionHosts.has(host);

    siteAppearance.addEventListener("change", async () => {
      if (siteAppearance.value === "inherit") delete siteModes[host];
      else siteModes[host] = siteAppearance.value;
      disabledHosts.delete(host);
      await browser.storage.local.set({
        siteModes,
        disabledHosts: [...disabledHosts].sort(),
      });
      await reload();
    });
    siteTextScale.addEventListener("change", async () => {
      const scale = Number(siteTextScale.value);
      if (scale === 100) delete siteTextScales[host];
      else siteTextScales[host] = scale;
      await browser.storage.local.set({ siteTextScales });
      await reload();
    });
    siteReduceMotion.addEventListener("change", async () => {
      if (siteReduceMotion.checked) reducedMotionHosts.add(host);
      else reducedMotionHosts.delete(host);
      await browser.storage.local.set({
        reducedMotionHosts: [...reducedMotionHosts].sort(),
      });
      await reload();
    });
  }
})();
