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
