# Acute Web Privacy

Acute Web is designed to browse without Acute or CORE collecting telemetry,
diagnostics, crash reports, browsing history, page contents, or advertising
identifiers.

Browsing data such as history, bookmarks, passwords, downloads, open tabs, and
Midnight Pages preferences stays on the device unless the user explicitly uses
an external service. Websites, search providers, installed extensions, and any
optional account or synchronization services have their own privacy practices.

## Private by default

Starting with Acute Web 2.0, every profile uses these protections unless the
user changes them in Settings › Privacy and security:

- **Strict tracking protection** blocks known trackers, fingerprinters,
  cryptominers and cross-site tracking content.
- **HTTPS-Only mode** loads websites only over secure connections.
- **Global Privacy Control** asks websites not to sell or share personal data.

A setting the user already chose before updating is kept. Strict protection can
break some embedded videos, comment sections or sign-in buttons; tapping the
shield in the address bar turns protection off for that site only.

### Home networks and self-hosted services

Loopback and private-network IP addresses (`localhost`, `127.x.x.x`, `10.x.x.x`,
`172.16.x.x`–`172.31.x.x`, `192.168.x.x`) are never forced to HTTPS, so routers,
NAS boxes and other devices reached by IP address open normally. Devices reached
by a local host name such as `nas.lan` or `homeassistant.local` show the
HTTPS-Only notice; choose **Continue to HTTP site** to open them. That exception
currently lasts until Acute is closed. HTTPS-Only can also be turned off in
Settings › Privacy and security › HTTPS-Only mode.

Acute Web uses Mozilla's open-source Gecko engine. Required open-source license
notices and source availability are provided in the app and in this repository.

Security issues should be reported according to [SECURITY.md](../SECURITY.md).
Ordinary bugs and feature requests belong on the
[GitHub Issues page](https://github.com/iiankehn/acute-web-android/issues).

## Telemetry startup hardening (Beta 3)

The overlay replaces the pinned Fenix `initializeGlean` implementation with a
no-op, preserving its signature for startup and onboarding callers. It no
longer registers Fenix pings, applies remote metric configuration, creates the
Glean upload client, initializes the backend or restores diagnostic tags.
Existing upload-consent and crash-service restrictions remain in place.

This is source evidence, not a network-capture result. Engine-level telemetry,
Firebase/web push and other retained services still require runtime inspection.
The Beta 3 privacy exit gate remains open until startup, first run, idle,
browsing and update-check traffic have been captured and reviewed.

## Local crash records (Beta 3 development)

Acute retains the most recent main-process Java/Kotlin crash in its private
backup-excluded directory. The bounded record includes app version, Android
version, model, exception types and up to 12 frames per cause (three causes,
4,000 characters maximum). It omits exception messages, filenames, thread
names and suppressed exceptions. It does not read page contents, browsing
history, URLs, account data or native crash dumps. Native engine/tab crashes
are outside this handler. Android itself may retain system crash logs under
its own settings.

Nothing is uploaded automatically. About or Settings › Report an issue offers
Include last crash (off by default), then an editable preview. Opening the
GitHub draft sends its approved text to GitHub in a URL, which the browser may
retain in history; submitting it creates a public issue. Canceling before
opening the URL sends nothing. Delete local crash removes the retained record;
a later crash replaces it. Device validation remains pending.

## Firebase messaging source review (Beta 3)

The pinned Fenix manifest enables Firebase messaging auto-initialization, while
setting `firebase_analytics_collection_enabled=false` and
`firebase_analytics_collection_deactivated=true`. These are distinct controls:
disabled Firebase analytics does not mean Firebase messaging is disabled.

The retained Firebase push implementation initializes Firebase, handles token
refresh, checks Google Play Services availability, and forwards channel-tagged
messages to Android Components AutoPush. Its callers support Web Push and
Send Tab. Fenix checks for a configured push project ID before creating its
AutoPush configuration; this source check alone does not prove whether a
particular Acute APK registers with Firebase or which hosts it contacts.

Acute removes the upstream log statements containing the Firebase registration
token and received message channel ID. The transport and callbacks are retained
while their runtime behavior is audited. This is an interim implementation
state, not a completed keep/remove decision or proof of zero network activity.

Source evidence at immutable Firefox `08d23041955657e661eef22c8fdc967735300233`:

- `mobile/android/fenix/app/src/main/AndroidManifest.xml`
- `mobile/android/fenix/app/src/main/java/org/mozilla/fenix/components/Push.kt`
- `mobile/android/fenix/app/src/main/java/org/mozilla/fenix/push/FirebasePushService.kt`
- `mobile/android/android-components/components/lib/push-firebase/src/main/java/mozilla/components/lib/push/firebase/AbstractFirebasePushService.kt`

Remaining evidence: inspect the candidate APK configuration and capture startup,
first-run, idle and push-related traffic on emulator environments with and
without Google Play Services. Record destinations and configuration without
publishing registration tokens or message identifiers. The privacy gate stays
open until observed behavior and product disclosures agree.
