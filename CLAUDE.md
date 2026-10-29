@../brain/CORE.md

# Acute Web for Android

Privacy-focused browser built from a pinned Firefox for Android (Fenix/Gecko)
commit. This repo holds no Mozilla source: `scripts/apply_overlay.py` patches an
upstream checkout in CI, and `overlay/` holds the resources and Kotlin it copies in.
Shared CORE context is imported above from the `brain` repo; if it is missing,
ask the user to clone `iiankehn/brain` beside this repo.

## Commands

```bash
make check   # project metadata consistency
make test    # Python regression tests (overlay fixtures, site release, APK checks)
make audit   # check + test + compile + security/release audit; CI's first gate
```

`make audit` takes seconds and needs only Python 3.12. Run it before every push.
APKs cannot be built in a cloud container. Full builds run in the **Build Android
APK** workflow (tag push, `beta` push or manual dispatch).

## Layout

| Path | Purpose |
|---|---|
| `acute-android.toml` | Product, channel, upstream pin and privacy metadata |
| `scripts/apply_overlay.py` | Every upstream patch; fails closed via `replace_once` |
| `overlay/` | Resources, Kotlin (`GitHubUpdateProvider.kt`), Midnight extension |
| `tests/` | `unittest` suites; overlay tests use inline upstream fixtures |
| `docs/` | Product website (acute.iiankehn.com) plus policy docs |
| `scripts/update_site_release.py` | Release job that updates `docs/index.html` |

## Rules

- Branches: `main` = Stable, `beta` = active development. Features land on
  `beta` and are promoted after phone, tablet, upgrade and update-channel testing
  (`docs/RELEASE_CHANNELS.md`).
- Every upstream patch must match exactly once or raise `OverlayError`. Never
  make a patch silently optional. Add a fixture and test with each patch.
- The Firefox pin lives in `acute-android.toml`, `PINNED_FIREFOX_REF` and the
  workflow-dispatch default. Change all three together, and only after review.
- GitHub Actions are pinned to full commit SHAs (the audit enforces it).
- Telemetry, crash upload, diagnostics and marketing stay disabled.
- Branding: "Acute Web" / "Acute Web by CORE". Firefox or Mozilla names only in
  accurate legal, license, source and engine disclosures.
- Never commit APKs, keystores, credentials or Mozilla source trees.
- Commit messages: plain imperative sentence, no prefix
  (e.g. "Isolate native APK architectures to prevent splash-screen startup crashes").

## Skills

- `acute-overlay-patch`: add or change an upstream patch with tests.
- `acute-android-release`: cut a Beta or Stable release and verify the website update.
