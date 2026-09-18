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
`main` for the first smoke test. The unsigned-production/debug-signed test APK
will be available as a workflow artifact. A second artifact contains portrait
and landscape screenshots from the automated tablet smoke pass. Android may
require permission to install unknown apps.

## Publish a signed sideload release

Complete `docs/SIGNING.md`, then tag a release:

```bash
git tag -a v0.1.0 -m "Acute Web 0.1.0"
git push origin v0.1.0
```

The workflow derives the app version `0.1.0` from the tag, signs the universal
APK, installs it in the tablet emulator, and publishes the GitHub Release only
after the tablet smoke test passes. Existing installations will see the release
through the built-in update checker.

## Recommended repository settings

- Enable Actions with read/write workflow permissions.
- Enable private vulnerability reporting.
- Protect `main` and require the validation workflow.
- Restrict who can create tags matching `v*`.
- Never expose signing secrets to workflows from untrusted pull requests.
