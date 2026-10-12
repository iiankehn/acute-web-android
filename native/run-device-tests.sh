#!/usr/bin/env bash
set -euo pipefail
./gradlew --no-daemon --max-workers=2 :app:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.notClass=com.acuteweb.nativeapp.ProcessDeathDeviceTest
run_stage() {
  local stage="$1"
  local result_file
  result_file="$(mktemp)"
  adb shell am instrument -w -e class "com.acuteweb.nativeapp.ProcessDeathDeviceTest#$stage" \
    com.acuteweb.browser.dev.test/androidx.test.runner.AndroidJUnitRunner | tee "$result_file"
  grep -Eq '^OK \(1 test\)' "$result_file"
  rm -f "$result_file"
}
run_stage prepare
adb shell am force-stop com.acuteweb.browser.dev
run_stage verify
