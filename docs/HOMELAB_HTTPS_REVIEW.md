# Homelab HTTPS-Only API review

Reviewed against Firefox `08d23041955657e661eef22c8fdc967735300233`
(the current Acute upstream pin). This is source evidence, not runtime testing.

## Findings

| Surface | Pinned-source evidence | Consequence for Acute |
|---|---|---|
| GeckoView permissions | `ContentPermission.convertType` maps a fixed set of permission types; HTTPS-Only exceptions are absent. `fromBundleArray` filters unknown types. The reverse mapping returns an empty string for unsupported integers. | `StorageController.getPermissions` / `setPermission` do not expose a supported HTTPS-Only exception type. An arbitrary integer or fabricated permission is not a supported persistence API. |
| Android Components | `GeckoPermissionRequest.Content.permissionsMap` covers notifications, location, autoplay, persistent storage, media keys, storage access and local-network/device access. | Local-network access permissions are not HTTPS-Only bypass permissions. Granting them does not implement the requested feature. |
| Error page | `lowMediumErrorPages.js` binds the continue button to `document.reloadWithHttpsOnlyException()`. GeckoSession documents that method for custom error pages. | The existing explicit continue action is available. The reviewed API does not give that call a persistent/per-site option. |
| Engine exemptions | `nsHTTPSOnlyUtils::LoopbackOrLocalException` recognizes `localhost`, `::1`, loopback addresses and eligible local IP literals. Non-IP host strings fail `NetAddr::InitFromString`. | `.local`, `.lan`, `.home.arpa` and `.internal` do not automatically qualify merely because of their suffix. DNS resolving to a private address is not checked by this function. |
| Native permission store | `TestIfPrincipalIsExempt` tests `https-only-load-insecure` and recognizes permanent/session allow values. | Gecko has an internal exception mechanism, but it is not mapped by the reviewed Java content-permission bridge. Changing vendored native source does not change Acute's prebuilt Gecko artifacts. |

## Beta 3 disposition

No supported implementation path was found through the reviewed public
GeckoView/Android Components permission APIs. Keep the existing explicit
Continue to HTTP site flow and current documented behavior. Persistent
exceptions, exception management in Settings and automatic local-name
exemptions are **not implemented** by this investigation.

Do not substitute a global HTTPS-Only toggle, silently rewrite all local-name
navigation, fabricate a permission constant, or persist private-browsing host
history as a workaround. These would not provide a correctly scoped engine
exception and could weaken the current protection.

The implementation remains deferred pending a supported upstream bridge or a
separately reviewed engine integration. This is a scoped source-review result,
not proof that every possible privileged/internal integration is impossible.
Recheck this finding when the upstream pin changes. Runtime exception lifetime,
redirect behavior and private-session isolation still need automated evidence;
this review does not mark those checks passed.

## Sources (immutable pin)

- [GeckoSession.java: permission types, mappings, filtering and error-page API](https://github.com/mozilla-firefox/firefox/blob/08d23041955657e661eef22c8fdc967735300233/mobile/android/geckoview/src/main/java/org/mozilla/geckoview/GeckoSession.java)
- [StorageController.java: permission read/write APIs](https://github.com/mozilla-firefox/firefox/blob/08d23041955657e661eef22c8fdc967735300233/mobile/android/geckoview/src/main/java/org/mozilla/geckoview/StorageController.java)
- [GeckoPermissionRequest.kt: Android Components mapping](https://github.com/mozilla-firefox/firefox/blob/08d23041955657e661eef22c8fdc967735300233/mobile/android/android-components/components/browser/engine-gecko/src/main/java/mozilla/components/browser/engine/gecko/permission/GeckoPermissionRequest.kt)
- [lowMediumErrorPages.js: continue action](https://github.com/mozilla-firefox/firefox/blob/08d23041955657e661eef22c8fdc967735300233/mobile/android/fenix/app/src/main/assets/lowMediumErrorPages.js)
- [nsHTTPSOnlyUtils.cpp: native exemptions and permission check](https://github.com/mozilla-firefox/firefox/blob/08d23041955657e661eef22c8fdc967735300233/dom/security/nsHTTPSOnlyUtils.cpp)
