# Acute Web 2.0.0 Beta 2 — draft release notes

Draft for the GitHub release text. Update the "What's Changed" list from the
merged pull requests before tagging `v2.0.0-beta.2`.

## Private by default

Acute now protects every profile with **Strict tracking protection**,
**HTTPS-Only mode** and **Global Privacy Control** out of the box.

- New installs see a "Private by default" page during first run.
- Updating from Beta 1 shows a one-time notice. Settings you already changed are
  kept.
- Settings › Privacy and security summarizes the defaults at the top.

If a site doesn't look right, tap the shield in the address bar to turn
protection off for that site.

**Home networks:** devices reached by IP address (`192.168.x.x`, `10.x.x.x` and
other private ranges) open normally. Devices reached by a local host name such
as `nas.lan` show the HTTPS-Only notice; choose **Continue to HTTP site**. See
[Privacy](https://github.com/iiankehn/acute-web-android/blob/main/docs/PRIVACY.md).

## Also in this Beta

- **Fixed:** opening the main menu (⋮) on a web page crashed the app (#12).
- Settings are grouped into focused categories: General, Appearance, Privacy and
  security, Passwords and autofill, Browsing data, Downloads and links,
  Extensions, Advanced and About.
- First-run artwork uses the Acute mark.
- The welcome page states Acute's own facts: open-source licensing and no
  telemetry, diagnostics or crash reports.
- Acute no longer re-prompts you on later days to set it as your default
  browser, sign in to sync or try a VPN.

## Known issues

- "Continue to HTTP site" exceptions for local host names last until Acute is
  closed.
