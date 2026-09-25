# APK signing

Android accepts an app update only when the new APK is signed by the same key
as the installed version. The Acute Web release key is therefore part of the
product's long-term update identity. Losing it prevents existing installations
from upgrading in place; exposing it allows an attacker to impersonate a
release.

## Key generation

Generate the key on a trusted local machine with a current JDK:

```bash
keytool -genkeypair -v \
  -keystore acute-web-release.jks \
  -alias acute-web \
  -keyalg RSA -keysize 4096 -validity 10000
```

Never place the keystore in the repository. Maintain at least two encrypted,
offline backups in separate locations.

## GitHub Actions configuration

Encode the keystore without line breaks:

```bash
base64 -w 0 acute-web-release.jks
```

On macOS:

```bash
base64 < acute-web-release.jks | tr -d '\n'
```

Create a protected GitHub Actions environment named `release-signing` and add:

| Secret | Value |
|---|---|
| `ACUTE_KEYSTORE_B64` | Base64-encoded keystore |
| `ACUTE_KEYSTORE_PASSWORD` | Keystore password |
| `ACUTE_KEY_ALIAS` | `acute-web` or the selected alias |
| `ACUTE_KEY_PASSWORD` | Private-key password |

Only the isolated signing job may access these values. Upstream source,
pull-request code, and the main compilation job must not receive them. Manual
workflow runs create debug-signed artifacts and never publish a release.

## Verification

Download the APK and inspect its signing certificate:

```bash
apksigner verify --verbose --print-certs acute-web-0.3.0-arm64-v8a.apk
```

Verify the accompanying SHA-256 checksum:

```bash
sha256sum -c acute-web-0.3.0-arm64-v8a.apk.sha256
```

Each stable release includes the APK checksum, signing-certificate report,
manifest-permissions report, exact build inputs, and provenance attestation.
Compare the certificate digest with a previously trusted Acute release before
installing an update. Record the production certificate digest somewhere
independent of GitHub.
