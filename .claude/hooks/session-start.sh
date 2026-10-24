#!/bin/bash
# Prepare a Claude Code cloud session for Acute Web work: the Android SDK tools
# that the APK verifiers and scripts/android_smoke.py use (adb, aapt2,
# apksigner, zipalign), plus a check that `make audit` can run.
#
# Idempotent: the SDK lives under $HOME and is reused when already present.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

SDK="${HOME}/android-sdk"
CMDLINE_ZIP="commandlinetools-linux-16111833_latest.zip"
CMDLINE_SHA1="e025545c62a8e64c7559119566a569fb1dec5f60"
BUILD_TOOLS="36.1.0"

if [ ! -x "${SDK}/cmdline-tools/latest/bin/sdkmanager" ]; then
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT
  curl -fsSL --retry 3 -o "${work}/${CMDLINE_ZIP}" \
    "https://dl.google.com/android/repository/${CMDLINE_ZIP}"
  echo "${CMDLINE_SHA1}  ${work}/${CMDLINE_ZIP}" | sha1sum -c --quiet -
  unzip -q "${work}/${CMDLINE_ZIP}" -d "${work}/unpacked"
  mkdir -p "${SDK}/cmdline-tools"
  rm -rf "${SDK}/cmdline-tools/latest"
  mv "${work}/unpacked/cmdline-tools" "${SDK}/cmdline-tools/latest"
fi

sdkmanager="${SDK}/cmdline-tools/latest/bin/sdkmanager"
if [ ! -x "${SDK}/platform-tools/adb" ] || [ ! -x "${SDK}/build-tools/${BUILD_TOOLS}/apksigner" ]; then
  # Current command-line tools accept the SDK licenses as part of install.
  "$sdkmanager" --sdk_root="$SDK" --install "platform-tools" "build-tools;${BUILD_TOOLS}" >/dev/null
fi

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export ANDROID_HOME=\"${SDK}\""
    echo "export ANDROID_SDK_ROOT=\"${SDK}\""
    echo "export PATH=\"${SDK}/platform-tools:${SDK}/build-tools/${BUILD_TOOLS}:${SDK}/cmdline-tools/latest/bin:\$PATH\""
  } >> "$CLAUDE_ENV_FILE"
fi

# The repository's own checks use only the Python standard library and Node.
python3 --version >/dev/null
node --version >/dev/null
