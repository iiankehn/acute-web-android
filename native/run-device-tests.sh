#!/usr/bin/env bash
set -euo pipefail
collect_failure() {
  local result=$?
  if [ "$result" -ne 0 ]; then
    mkdir -p app/build/reports/androidTests/diagnostics
    adb logcat -d -v threadtime > app/build/reports/androidTests/diagnostics/logcat.txt || true
    adb exec-out run-as com.acuteweb.browser.dev cat cache/popup-failure.png > app/build/reports/androidTests/diagnostics/popup-failure.png || true
  fi
  return "$result"
}
trap collect_failure EXIT
./gradlew --no-daemon --max-workers=2 :app:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.notClass=com.acuteweb.nativeapp.ProcessDeathDeviceTest
# Gradle removes instrumentation packages after connected tests. Install fresh
# fixtures for the two invocations that must share data across a force-stop.
adb install -r -t app/build/outputs/apk/debug/app-debug.apk
adb install -r -t app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
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
