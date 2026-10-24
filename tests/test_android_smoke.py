from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import android_smoke  # noqa: E402
from android_smoke import Smoke, SmokeFailure, find, parse_nodes  # noqa: E402

PACKAGE = "com.acuteweb.browser.dev"


def screen(*labels):
    """A UI dump with one row per label; ('desc', x) marks a content description."""
    rows = []
    for index, label in enumerate(labels):
        attribute = f'content-desc="{label[1]}" text=""' if isinstance(label, tuple) else f'text="{label}" content-desc=""'
        top = 100 + index * 100
        rows.append(f'<node {attribute} package="{PACKAGE}" bounds="[0,{top}][1000,{top + 80}]" />')
    return "<hierarchy>" + "".join(rows) + "</hierarchy>"


MENU = ("desc", "More options")
SCREENS = {
    "welcome": screen("Welcome to Acute Web", "Continue"),
    "private": screen("Private by default", "Continue"),
    "default": screen("Set as default browser", "Not now"),
    "home": screen("Search or enter address", MENU),
    "page": screen("example.com", "Example Domain", MENU),
    "menu": screen("Back", "Bookmarks", "Settings"),
    "settings-top": screen("General", "Search", "Appearance"),
    "settings-privacy": screen("Privacy and security", "Enhanced Tracking Protection", "HTTPS-Only Mode"),
    "https-only": screen("HTTPS-Only Mode", "Enable in all tabs"),
    "error": screen("Secure Site Not Available", "Continue to HTTP Site"),
}
TAPS = {
    ("welcome", "Continue"): "private",
    ("private", "Continue"): "default",
    ("default", "Not now"): "home",
    ("page", "More options"): "menu",
    ("menu", "Settings"): "settings-top",
    ("settings-privacy", "HTTPS-Only Mode"): "https-only",
}
SWIPES = {"settings-top": "settings-privacy"}
BACK = {"https-only": "settings-privacy", "settings-privacy": "page", "settings-top": "page", "menu": "page"}


class FakeAdb:
    def __init__(self):
        self.current = "welcome"
        self.in_front = True
        self.alive = True
        self.crash_log = ""
        self.tapped = []
        self.on_tap = None

    def run(self, *arguments, check=True, timeout=120):
        if arguments[:3] == ("logcat", "-d", "-b"):
            return self.crash_log
        return ""

    def pull_bytes(self, *arguments):
        return b"PNG"

    def shell(self, command, check=True, timeout=120):
        if command.startswith("uiautomator dump"):
            return "UI hierchary dumped to: /sdcard/acute-smoke.xml"
        if command.startswith("cat "):
            return SCREENS[self.current]
        if command == "dumpsys window":
            app = PACKAGE if self.in_front else "com.example.chat"
            return f"  mCurrentFocus=Window{{1 u0 {app}/{app}.MainActivity}}"
        if command.startswith("pidof"):
            return "4242\n" if self.alive else ""
        if command.startswith("monkey"):
            self.current = "welcome"
        elif command.startswith("am start"):
            self.current = "error" if "http://" in command else "page"
        elif command.startswith("input tap"):
            x, y = map(int, command.split()[2:4])
            node = next(n for n in parse_nodes(SCREENS[self.current]) if n.bounds[1] <= y <= n.bounds[3])
            self.tapped.append(node.label())
            if self.on_tap:
                self.on_tap(node.label())
            self.current = TAPS.get((self.current, node.label()), self.current)
        elif command.startswith("input swipe"):
            self.current = SWIPES.get(self.current, self.current)
        elif command == "input keyevent 4":
            self.current = BACK.get(self.current, self.current)
        elif command == "wm size":
            return "Physical size: 1080x1920"
        return ""


class SmokeTests(unittest.TestCase):
    def smoke(self, adb):
        clock = iter(range(0, 10_000))
        output = Path(tempfile.mkdtemp())
        return Smoke(adb, PACKAGE, output, sleep=lambda _: None, clock=lambda: next(clock))

    def run_all(self, adb):
        smoke = self.smoke(adb)
        for check in (smoke.launch, smoke.first_run, smoke.https_page, smoke.menu, smoke.settings,
                      smoke.http_page, smoke.finish):
            check()
        return smoke

    def test_full_flow_passes_and_never_changes_system_settings(self):
        adb = FakeAdb()
        self.run_all(adb)
        self.assertEqual(adb.tapped, ["Continue", "Continue", "Not now", "More options", "Settings", "HTTPS-Only Mode"])
        self.assertNotIn("Set as default browser", adb.tapped)

    def test_stops_without_tapping_when_another_app_is_in_front(self):
        adb = FakeAdb()
        smoke = self.smoke(adb)
        smoke.launch()
        adb.in_front = False
        with self.assertRaisesRegex(SmokeFailure, "isn't the app in front"):
            smoke.first_run()
        self.assertEqual(adb.tapped, [])

    def test_crash_during_menu_fails_with_the_stack(self):
        adb = FakeAdb()

        def crash_on_menu(label):
            if label == "More options":
                adb.crash_log = ("--------- beginning of crash\nE AndroidRuntime: FATAL EXCEPTION: main\n"
                                 f"E AndroidRuntime: Process: {PACKAGE}, PID: 4242\n"
                                 "E AndroidRuntime: java.lang.IllegalStateException: nested scroll\n")
        adb.on_tap = crash_on_menu
        with self.assertRaisesRegex(SmokeFailure, "(?s)crashed during.*nested scroll"):
            self.run_all(adb)

    def test_stopped_process_fails(self):
        adb = FakeAdb()
        smoke = self.smoke(adb)
        smoke.launch()
        adb.alive = False
        with self.assertRaisesRegex(SmokeFailure, "stopped running"):
            smoke.first_run()

    def test_other_packages_crashes_are_not_ours(self):
        adb = FakeAdb()
        adb.crash_log = "E AndroidRuntime: FATAL EXCEPTION: main\nE AndroidRuntime: Process: com.acuteweb.browser.dev, PID: 1\n"
        stable = Smoke(adb, "com.acuteweb.browser", Path(tempfile.mkdtemp()))
        self.assertEqual(stable.crash_report(), "")
        self.assertIn("FATAL EXCEPTION", self.smoke(adb).crash_report())

    def test_first_run_that_never_reaches_home_fails(self):
        adb = FakeAdb()
        smoke = self.smoke(adb)
        smoke.launch()
        adb.current = "default"
        TAPS_BACKUP = dict(TAPS)
        TAPS.pop(("default", "Not now"))
        try:
            with self.assertRaisesRegex(SmokeFailure, "didn't reach the home screen"):
                smoke.first_run()
        finally:
            TAPS.clear()
            TAPS.update(TAPS_BACKUP)

    def test_run_reports_failure_and_saves_evidence(self):
        adb = FakeAdb()
        adb.alive = False
        clock = iter(range(0, 10_000))
        with tempfile.TemporaryDirectory() as directory:
            code = android_smoke.run(adb, PACKAGE, Path(directory), apk=None, fresh=False,
                                     sleep=lambda _: None, clock=lambda: next(clock))
            self.assertEqual(code, 1)
            self.assertTrue((Path(directory) / "failure.png").is_file())

    def test_parse_nodes_skips_unlabelled_and_empty_bounds(self):
        dump = ('<hierarchy><node text="" content-desc="" bounds="[0,0][10,10]" />'
                '<node text="Hi" content-desc="" bounds="[5,5][5,9]" />'
                '<node text="" content-desc="More options" bounds="[0,0][100,50]" /></hierarchy>')
        nodes = parse_nodes(dump)
        self.assertEqual([n.label() for n in nodes], ["More options"])
        self.assertEqual(nodes[0].center, (50, 25))
        self.assertIsNotNone(find(nodes, description="More options"))
        self.assertIsNone(find(nodes, text="More"))
        self.assertIsNotNone(find(nodes, description="More", contains=True))


if __name__ == "__main__":
    unittest.main()
