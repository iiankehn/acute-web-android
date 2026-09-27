#!/usr/bin/env bash
set -euo pipefail

apk_path="${1:?usage: tablet_smoke.sh APK OUTPUT_DIRECTORY}"
output_dir="${2:?usage: tablet_smoke.sh APK OUTPUT_DIRECTORY}"
package_name="${ACUTE_PACKAGE_NAME:-com.acuteweb.browser.debug}"
page_url="${ACUTE_SCREENSHOT_URL:-https://en.wikipedia.org/wiki/Web_browser}"

mkdir -p "$output_dir"
adb wait-for-device
adb install -r "$apk_path"

reset_display() {
  adb shell wm size reset >/dev/null 2>&1 || true
  adb shell wm density reset >/dev/null 2>&1 || true
  adb shell settings put system accelerometer_rotation 1 >/dev/null 2>&1 || true
}
trap reset_display EXIT

capture_diagnostics() {
  local name="$1"
  local orientation="$2"
  adb shell dumpsys activity activities > "$output_dir/${name}-${orientation}-activity.txt" 2>&1 || true
  adb shell dumpsys window windows > "$output_dir/${name}-${orientation}-window.txt" 2>&1 || true
  adb logcat -d -t 500 > "$output_dir/${name}-${orientation}-logcat.txt" 2>&1 || true
}

run_profile() {
  local name="$1"
  local size="$2"
  local density="$3"

  adb shell wm size "$size"
  adb shell wm density "$density"
  adb shell settings put system accelerometer_rotation 0

  for rotation in 0 1; do
    local orientation="portrait"
    if [[ "$rotation" == "1" ]]; then orientation="landscape"; fi
    adb shell settings put system user_rotation "$rotation"
    adb shell am force-stop "$package_name"
    adb shell monkey -p "$package_name" -c android.intent.category.LAUNCHER 1 >/dev/null
    # Emulator startup can take longer after changing tablet size/density.
    # Wait for the browser process instead of failing on a fixed 4-second delay.
    launched=false
    for _ in {1..20}; do
      if adb shell pidof "$package_name" >/dev/null 2>&1; then
        launched=true
        break
      fi
      sleep 1
    done
    if [[ "$launched" != "true" ]]; then
      echo "Browser failed to stay running for $name $orientation" >&2
      capture_diagnostics "$name" "$orientation"
      return 1
    fi
    if ! adb shell am start -W \
      -a android.intent.action.VIEW \
      -d "$page_url" \
      -p "$package_name" > "$output_dir/${name}-${orientation}-launch.txt" 2>&1; then
      capture_diagnostics "$name" "$orientation"
      return 1
    fi
    sleep 10
    # Put text and imagery underneath the browser chrome so screenshots verify
    # CORE Glass transparency against real page content, not an empty homepage.
    adb shell input swipe 600 1500 600 500 500 >/dev/null 2>&1 || true
    sleep 2
    if ! adb shell pidof "$package_name" >/dev/null 2>&1; then
      capture_diagnostics "$name" "$orientation"
      return 1
    fi
    if ! adb exec-out screencap -p > "$output_dir/${name}-${orientation}.png" ||
      [[ ! -s "$output_dir/${name}-${orientation}.png" ]]; then
      capture_diagnostics "$name" "$orientation"
      return 1
    fi
  done
}

run_profile compact-phone 1080x1920 420
run_profile compact-tablet 1200x1920 240
run_profile standard-tablet 1600x2560 320
run_profile large-tablet 1848x2960 320

adb shell dumpsys package "$package_name" > "$output_dir/package.txt"
echo "Generic phone and tablet smoke tests passed for $package_name"
