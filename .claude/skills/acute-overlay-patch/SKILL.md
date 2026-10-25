---
name: acute-overlay-patch
description: Add or change an Acute Web patch to upstream Firefox for Android (Fenix, Android Components, Gecko resources) through scripts/apply_overlay.py, with fail-closed matching and regression fixtures. Use for any change to browser behavior, UI, branding, privacy defaults or manifests in acute-web-android.
---

# Add or change an overlay patch

Acute never forks Mozilla source. Every behavior change is a scripted, reviewable
patch applied to the pinned checkout in CI.

## 1. Locate the upstream code

- The pinned commit is `upstream.ref` in `acute-android.toml`. Read upstream files
  at that exact commit (for example
  `https://raw.githubusercontent.com/mozilla-firefox/firefox/<ref>/mobile/android/fenix/...`).
  Never patch against a moving branch.
- Prefer configuration, resources or overlay files over editing Kotlin, and
  prefer upstream features that already exist over new code.

## 2. Write the patch

- Add a `patch_<area>(path: Path)` function in `scripts/apply_overlay.py` near
  related patches, and call it from `apply()`. Add any new upstream file to the
  `required` list so a missing file fails the build.
- Use `replace_once(text, old, new, label)` for every edit. Choose an `old`
  anchor that is specific and stable. If it matches zero or more than one time
  the build must fail. That is the intended behavior.
- Channel-specific behavior takes `channel` (`"stable"` or `"beta"`).
- New resources or Kotlin go under `overlay/` (Beta-only launcher assets go
  under `overlay/beta-res/`) and are copied by `copy_overlay()`.

## 3. Test it

- In `tests/test_overlay.py`, extend the inline upstream fixture strings so the
  anchor exists, then assert:
  - the patched output contains the new behavior;
  - applying to a fixture **without** the anchor raises `OverlayError`.
- Run `make audit`. All of it must pass.

## 4. Check policy before committing

- No telemetry, network endpoints other than GitHub releases, or marketing surfaces.
- Phone and tablet behavior both considered; accessible labels kept.
- Branding rules in `CLAUDE.md` respected.
- Update `docs/MODIFICATIONS.md` when the user-visible product changes.
- If the feature should also exist on iOS, add a row to the parity table in
  `../brain/projects/acute-web.md`.

Explain in the PR that the APK is verified by the manual **Build Android APK**
workflow run, not by local tests.
