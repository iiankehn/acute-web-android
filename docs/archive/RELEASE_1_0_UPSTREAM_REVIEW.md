> Historical release rationale; the current input is recorded in `acute-android.toml`.

## 1.0 upstream review

The 1.0 candidate retains Firefox commit
`4452e9a17a29f762c5af6326f45c000dcf3117bb`, reviewed on September 28, 2026.
That input was eight days behind Mozilla's development head and had already
passed Acute's complete ARM64 build, signing-continuity checks, and physical
0.7 acceptance testing. Moving to the contemporary development head would
have introduced roughly 2,200 additional commits, including AndroidX, Gradle,
Android build-system, and Gecko changes, immediately before the final release.
The larger upstream refresh is therefore a post-1.0 Beta task and must pass the
same fail-closed audit and device-acceptance gates before later promotion.
