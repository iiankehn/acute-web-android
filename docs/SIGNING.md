# APK signing

Android accepts an update only when it is signed by the same key as the
installed app. Back up this key: losing it means existing users cannot upgrade.

## 1. Generate the key locally

Install a JDK, then run:

```bash
keytool -genkeypair -v \
  -keystore acute-web-release.jks \
  -alias acute-web \
  -keyalg RSA -keysize 4096 -validity 10000
```

Do not place the `.jks` file inside the repository. Keep at least two encrypted
offline backups.

## 2. Add GitHub Actions secrets

Encode the keystore without line breaks:

```bash
base64 -w 0 acute-web-release.jks
```

On macOS use `base64 < acute-web-release.jks | tr -d '\n'`.

Add these repository secrets under **Settings → Secrets and variables →
Actions**:

| Secret | Value |
|---|---|
| `ACUTE_KEYSTORE_B64` | Base64 output from the keystore |
| `ACUTE_KEYSTORE_PASSWORD` | Keystore password |
| `ACUTE_KEY_ALIAS` | `acute-web` (or the alias you selected) |
| `ACUTE_KEY_PASSWORD` | Private-key password |

Tag-triggered releases deliberately fail if any signing secret is absent.
Manual workflow runs create test builds and do not publish a release.

## 3. Verify a release

After downloading the APK, inspect its certificate:

```bash
apksigner verify --verbose --print-certs acute-web-0.1.0-universal.apk
```

Record the SHA-256 certificate digest somewhere independent of GitHub.

