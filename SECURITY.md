# Security policy

Security reports are taken seriously. Please do not disclose suspected
vulnerabilities in a public issue.

## Supported versions

Security fixes are provided through the newest stable Acute Web release.
Because the app is sideloaded, users must approve installation of each update
presented by the built-in updater.

| Version | Supported |
|---|---|
| Latest stable release | Yes |
| Older releases | No |

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** option on this repository's Security
page. Include:

- the affected Acute version and Android version;
- device model and architecture;
- clear reproduction steps;
- expected and observed behavior;
- crash output, logs, or a proof of concept when available;
- the potential impact and any known mitigations.

Do not include secrets, personal browsing data, or credentials. Allow
maintainers reasonable time to investigate and prepare a signed release before
public disclosure.

If the vulnerability is in Mozilla's upstream Firefox or Gecko code rather
than an Acute-specific change, also follow
[Mozilla's security bug reporting process](https://www.mozilla.org/security/#For_Developers).

## Release-key security

The Acute release keystore must never be committed. It is stored as protected
GitHub Actions environment secrets and is exposed only to the isolated signing
job. Upstream and pull-request code must never execute in a job or step that can
access those secrets.

See [APK signing](docs/SIGNING.md) for the release-key handling and verification
process.
