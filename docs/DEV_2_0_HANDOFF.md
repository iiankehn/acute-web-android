# Android 2.0 handoff

Android 2.0 keeps the Fenix application and Gecko engine, native Google/Material
controls, opaque Midnight surfaces, Android 12+, and separate ARM64/x86_64 APKs.
The independent GeckoView migration and CORE Glass remain shelved.

## Where to continue

Use [the Beta preparation audit](BETA_2_0_AUDIT.md) for current findings,
validation evidence and remaining acceptance gates. Inspect the live branch,
PR head and Actions results before resuming; build numbers in notes describe
specific historical commits.

The hardening work is tracked in [PR #7](https://github.com/iiankehn/acute-web-android/pull/7)
against `dev`. Stable, Beta and Dev use separate profiles; a Dev build does not
establish Beta install-over behavior or readiness for public release.

## Preserved history

- [Earlier handoffs and WIP checkpoints](archive/DEV_2_0_HANDOFF.md)
- [Earlier source security review](archive/DEV_2_0_SECURITY_AUDIT.md)

The archived notes describe past states and are not instructions to reset Dev,
resume the independent engine migration, or repeat completed build repairs.
