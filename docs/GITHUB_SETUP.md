# GitHub setup

## Create and push the public repository

With GitHub CLI installed and authenticated:

```bash
cd acute-web-android
git init
git add .
git commit -m "Initial Acute Web Android scaffold"
git branch -M main
gh repo create iiankehn/acute-web-android --public --source=. --remote=origin --push
```

If the repository already exists, replace the last command with:

```bash
git remote add origin https://github.com/iiankehn/acute-web-android.git
git push -u origin main
```

## Produce a test APK

Open **Actions → Build Android APK → Run workflow**. Leave the Firefox ref at
the audited 40-character commit shown by default. The debug-signed test APK
will be available as a workflow artifact. A second artifact contains Android 12
launch and rotation evidence. Android may require permission to install unknown
apps.

## Publish a signed sideload release

Complete `docs/SIGNING.md`, then tag a release:

```bash
git tag -a v0.1.0 -m "Acute Web 0.1.0"
git push origin v0.1.0
```

The workflow derives the app version from the tag, builds without release
secrets, passes an Android 12 smoke test, signs the APK in an isolated job,
verifies that the certificate matches v0.2.0, and publishes an immutable GitHub
Release with its checksum, build inputs, and provenance attestation. Existing
installations will see the release through the built-in update checker.

## Recommended repository settings

- Keep the default Actions token permission read-only. The publish job requests
  write access explicitly.
- Create a `release-signing` environment and restrict deployment to protected
  version tags. Add a required reviewer if your GitHub plan supports it.
- Enable private vulnerability reporting.
- Protect `main` and require the validation workflow.
- Restrict who can create tags matching `v*`.
- Never expose signing secrets to workflows from untrusted pull requests.
