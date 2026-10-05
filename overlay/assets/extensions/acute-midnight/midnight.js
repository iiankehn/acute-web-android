/* Acute Site Display — local-only per-domain rendering preferences. */
(async () => {
  "use strict";

  if (browser.extension.inIncognitoContext) return;
  if (!/^https?:$/.test(location.protocol)) return;

  const contentType = (document.contentType || "").toLowerCase();
  if (contentType === "application/pdf") return;

  const sensitivePath = /(?:^|\/)(?:checkout|payment|payments|billing|wallet)(?:\/|$)/i;
  if (sensitivePath.test(location.pathname)) return;

  const host = location.hostname.toLowerCase();
  const {
    mode = "automatic",
    disabledHosts = [],
    siteModes = {},
    siteTextScales = {},
    reducedMotionHosts = [],
  } = await browser.storage.local.get([
    "mode",
    "disabledHosts",
    "siteModes",
    "siteTextScales",
    "reducedMotionHosts",
  ]);
  const siteMode = siteModes[host] || (disabledHosts.includes(host) ? "original" : "inherit");
  const effectiveMode = siteMode === "dark" ? "always" : siteMode === "original" ? "off" : mode;
  const textScale = [90, 100, 110, 125, 150].includes(Number(siteTextScales[host]))
    ? Number(siteTextScales[host])
    : 100;
  const reduceMotion = reducedMotionHosts.includes(host);

  const hasNativeDarkSignal = () => {
    const declared = document.querySelector(
      'meta[name="color-scheme" i], meta[name="supported-color-schemes" i]',
    );
    if (declared && /dark/i.test(declared.content || "")) return true;

    const scheme = getComputedStyle(document.documentElement).colorScheme;
    return /(?:^|\s)dark(?:\s|$)/i.test(scheme);
  };

  const hasDarkBackground = () => {
    const color = getComputedStyle(document.body || document.documentElement).backgroundColor;
    const match = color.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if (!match) return false;
    const [, red, green, blue] = match.map(Number);
    const luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255;
    return luminance < 0.32;
  };

  const applyPreferences = () => {
    const style = document.createElement("style");
    style.id = "acute-site-display";
    const rules = [];

    if (textScale !== 100) {
      rules.push(`html { zoom: ${textScale / 100} !important; }`);
    }
    if (reduceMotion) {
      rules.push(`
        html { scroll-behavior: auto !important; }
        *, *::before, *::after {
          animation-duration: 0.001ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.001ms !important;
        }
      `);
    }
    const shouldDarken =
      effectiveMode !== "off" &&
      !(effectiveMode === "automatic" && (hasNativeDarkSignal() || hasDarkBackground()));
    if (shouldDarken) {
      rules.push(`
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
      `);
    }
    if (rules.length === 0) return;
    style.textContent = rules.join("\n");
    (document.head || document.documentElement).appendChild(style);
    document.documentElement.dataset.acuteSiteDisplay = "on";
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyPreferences, { once: true });
  } else {
    applyPreferences();
  }
})();
