/* Acute Midnight Pages — local-only Beta rendering experiment. */
(async () => {
  "use strict";

  if (browser.extension.inIncognitoContext) return;
  if (!/^https?:$/.test(location.protocol)) return;

  const contentType = (document.contentType || "").toLowerCase();
  if (contentType === "application/pdf") return;

  const sensitivePath = /(?:^|\/)(?:checkout|payment|payments|billing|wallet)(?:\/|$)/i;
  if (sensitivePath.test(location.pathname)) return;

  const host = location.hostname.toLowerCase();
  const { mode = "automatic", disabledHosts = [] } =
    await browser.storage.local.get(["mode", "disabledHosts"]);

  if (mode === "off" || disabledHosts.includes(host)) return;

  const hasNativeDarkSignal = () => {
    const declared = document.querySelector(
      'meta[name="color-scheme" i], meta[name="supported-color-schemes" i]',
    );
    if (declared && /dark/i.test(declared.content || "")) return true;

    const scheme = getComputedStyle(document.documentElement).colorScheme;
    return /(?:^|\s)dark(?:\s|$)/i.test(scheme);
  };

  const enable = () => {
    if (mode === "automatic" && hasNativeDarkSignal()) return;
    const style = document.createElement("style");
    style.id = "acute-midnight-pages";
    style.textContent = `
      :root { color-scheme: dark !important; background: #090d12 !important; }
      html, body { background-color: #090d12 !important; color: #dfe7ef !important; }
      body :where(main, article, section, nav, aside, header, footer, div) {
        background-color: transparent !important;
        border-color: #33404d !important;
      }
      :where(input, textarea, select, button) {
        background-color: #18222c !important;
        color: #eef6ff !important;
        border-color: #405367 !important;
      }
      :where(a, a:visited) { color: #69bff2 !important; }
      :where(pre, code) { background-color: #121a22 !important; color: #d9e8f6 !important; }
      :where(img, video, canvas, svg, picture) { color-scheme: normal !important; }
    `;
    (document.head || document.documentElement).appendChild(style);
    document.documentElement.dataset.acuteMidnight = "on";
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enable, { once: true });
  } else {
    enable();
  }
})();
