# Waydroid startup failure and native package isolation

The supplied Stable crash log shows `UnsatisfiedLinkError: Unable to load library
'xul'` during `FenixApplication.onCreate`, through Glean's crash-reporter
initialization. It requests x86_64 `libxul.so`, which the loader cannot find.
This failure happens before the browser UI is created.

Inspection of the published 1.1.0 ARM64 APK found a complete ARM64 engine plus
partial x86_64 and ARMv7 dependency libraries. The ARM64 package therefore
advertises x86_64 native compatibility without an x86_64 engine. The published
x86_64 package also has partial foreign ARM libraries. Checking only that the
intended engine exists did not detect this defect. The log does not establish
the installed APK filename; reproduction on the affected device is still needed.

Each build now requires `ACUTE_TARGET_ABI` to match its Gecko artifact target.
Gradle excludes every other native architecture, and ABI splits use that same
target. A package verifier rejects foreign ABI folders, missing engine/JNA/
application-services libraries, and wrongly labelled ELF binaries before upload
or signing. The fix applies independently to Stable and Beta.

For local builds, set `ACUTE_TARGET_ABI=arm64-v8a` after an aarch64 artifact build
or `ACUTE_TARGET_ABI=x86_64` after an x86_64 artifact build when invoking Gradle.
This setting does not convert or rebuild Gecko for another architecture.

## Device acceptance

- Install the corrected x86_64 APK for the matching channel over the existing
  application; retain user data.
- Confirm first launch passes the splash screen and that a real page loads.
- Confirm tabs, rotation, and keyboard/mouse navigation still work.
- Repeat for both Stable and Beta, and check ARM64 launches on an ARM64 device.
- Inspect `dumpsys package com.acuteweb.browser` (or `.beta`) to confirm Android
  selected `primaryCpuAbi=x86_64` on Waydroid.
- If startup still fails, capture a new log; a different exception is a separate
  failure, and missing libraries in the actual installed package must be checked.

Build/package checks do not certify Waydroid runtime compatibility. No graphics,
sandbox, or telemetry-upload settings are changed by this fix.
