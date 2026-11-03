#!/usr/bin/env python3
"""Drive an installed Acute build through its core screens over adb.

The same checks run on CI emulators and on a tester's phone:

1. launch and get through first run to the home screen;
2. load an HTTPS page;
3. open the main menu on that page and scroll it (the Beta 1 crash);
4. open Settings, find Privacy and security, and open HTTPS-Only Mode;
5. load an HTTP-only site and expect the HTTPS-Only warning page;
6. review and cancel an issue draft without opening GitHub;
7. finish with the browser still running and no crash recorded.

Before every tap, swipe or key press the script confirms Acute is the app in
front, so it never touches another app on a phone someone is using.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


HOME_TEXT = "Search or enter address"
MENU_DESCRIPTION = "More options"
MENU_HEADING = "Navigation"  # Acute's first main-menu group; Settings is at the bottom
SETTINGS_TEXT = "Settings"
PRIVACY_CATEGORY = "Privacy and security"
HTTPS_ONLY_SETTING = "HTTPS-Only Mode"
HTTPS_ONLY_ERROR = "Secure site not available"  # Gecko's page title; matched ignoring case
HTTPS_PAGE = "https://example.com/"
HTTPS_PAGE_MARKERS = ("example.com", "Example Domain")
# httpforever.com refuses every TLS handshake, so HTTPS-Only can never upgrade
# it. (neverssl.com has a valid certificate and sometimes answers over HTTPS.)
HTTP_ONLY_PAGE = "http://httpforever.com/"

# First-run buttons that only move forward or decline. Buttons that change
# system state (default browser, notifications, Sync) are never tapped.
FIRST_RUN_BUTTONS = ("Continue", "Not now", "Skip", "No Thanks", "No", "Done", "Continue browsing")
FIRST_RUN_STEPS = 12
# Android's own "Set Acute as your default browser app?" dialog, which upstream
# first run opens. Answering Cancel declines and changes nothing.
DEFAULT_BROWSER_PROMPT = re.compile(r"^Set .*Acute.* as your default browser app\?$")
PERMISSION_CONTROLLER = "permissioncontroller/"


class SmokeFailure(Exception):
    """A check failed; the message says which one and what was on screen."""


@dataclass(frozen=True)
class Node:
    text: str
    description: str
    package: str
    bounds: tuple[int, int, int, int]
    checked: bool | None = None

    @property
    def center(self) -> tuple[int, int]:
        left, top, right, bottom = self.bounds
        return (left + right) // 2, (top + bottom) // 2

    def label(self) -> str:
        return self.text or self.description


BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


def parse_nodes(dump: str) -> list[Node]:
    """Parse a `uiautomator dump` document into visible, labelled nodes."""
    nodes = []
    for element in ET.fromstring(dump).iter("node"):
        match = BOUNDS.fullmatch(element.get("bounds", ""))
        if not match:
            continue
        bounds = tuple(int(value) for value in match.groups())
        if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            continue
        text = element.get("text", "").strip()
        description = element.get("content-desc", "").strip()
        if text or description:
            nodes.append(Node(text, description, element.get("package", ""), bounds,
                              element.get("checked") == "true" if "checked" in element.attrib else None))
    return nodes


def find(nodes: list[Node], *, text: str | None = None, description: str | None = None,
         label: str | None = None, contains: bool = False, last: bool = False) -> Node | None:
    """Find a node by visible text, content description, or `label` (either one).

    `last` picks the final match, e.g. a menu item that shares its group heading's name.
    """
    for node in (reversed(nodes) if last else nodes):
        for wanted, actual in ((text, node.text), (description, node.description),
                               (label, node.text), (label, node.description)):
            if wanted is None:
                continue
            if (wanted in actual) if contains else (actual == wanted):
                return node
    return None


class Adb:
    """Thin adb wrapper; tests replace it with a scripted fake."""

    def __init__(self, serial: str | None = None):
        self.prefix = ["adb"] + (["-s", serial] if serial else [])

    def run(self, *arguments: str, check: bool = True, timeout: int = 120) -> str:
        result = subprocess.run(self.prefix + list(arguments), capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
        if check and result.returncode != 0:
            raise SmokeFailure(f"adb {' '.join(arguments)} failed: {result.stderr.strip() or result.stdout.strip()}")
        return result.stdout

    def shell(self, command: str, check: bool = True, timeout: int = 120) -> str:
        return self.run("shell", command, check=check, timeout=timeout)

    def pull_bytes(self, *arguments: str) -> bytes:
        return subprocess.run(self.prefix + list(arguments), capture_output=True, timeout=120).stdout


class Smoke:
    def __init__(self, adb: Adb, package: str, output: Path, *, sleep=time.sleep, clock=time.monotonic):
        self.adb = adb
        self.package = package
        self.output = output
        self.sleep = sleep
        self.clock = clock
        self.passed: list[str] = []

    # Observation -----------------------------------------------------------

    def nodes(self) -> list[Node]:
        last_error = ""
        for _ in range(5):
            dumped = self.adb.shell("uiautomator dump /sdcard/acute-smoke.xml", check=False)
            if "dumped to" in dumped.lower():
                return parse_nodes(self.adb.shell("cat /sdcard/acute-smoke.xml"))
            last_error = dumped.strip()
            self.sleep(1)
        raise SmokeFailure(f"Could not read the screen: {last_error}")

    def focus(self) -> list[str]:
        windows = self.adb.shell("dumpsys window", check=False)
        return [line for line in windows.splitlines() if "mCurrentFocus" in line or "mFocusedApp" in line]

    def in_front(self) -> bool:
        return any(self.package + "/" in line for line in self.focus())

    def default_browser_prompt(self, nodes: list[Node]) -> Node | None:
        """The Cancel button of Android's default-browser dialog for Acute, if that is what's in front."""
        if not any(DEFAULT_BROWSER_PROMPT.match(node.text) for node in nodes):
            return None
        if not any(PERMISSION_CONTROLLER in line for line in self.focus()):
            return None
        return find(nodes, text="Cancel")

    def running(self) -> bool:
        return bool(self.adb.shell(f"pidof {self.package}", check=False).strip())

    def crash_report(self) -> str:
        crashes = self.adb.run("logcat", "-d", "-b", "crash", check=False)
        match = re.search(rf"Process: {re.escape(self.package)}(?=[,\s]|$)", crashes)
        if match is None:
            return ""
        start = crashes.rfind("FATAL EXCEPTION", 0, match.start())
        return crashes[start if start >= 0 else match.start():][:4000]

    def wait_for(self, what: str, found, timeout: float = 60, step: float = 2) -> list[Node]:
        deadline = self.clock() + timeout
        while True:
            self.require_alive(what)
            nodes = self.nodes()
            if found(nodes):
                return nodes
            if self.clock() >= deadline:
                labels = ", ".join(node.label() for node in nodes[:25]) or "nothing readable"
                raise SmokeFailure(f"Timed out waiting for {what}. On screen: {labels}")
            self.sleep(step)

    def require_alive(self, during: str) -> None:
        report = self.crash_report()
        if report:
            raise SmokeFailure(f"Acute crashed during {during}:\n{report}")
        if not self.running():
            raise SmokeFailure(f"Acute stopped running during {during}")

    # Interaction (every action checks Acute is in front first) ------------

    def require_front(self, action: str) -> None:
        if not self.in_front():
            raise SmokeFailure(f"Stopped before {action}: Acute isn't the app in front, so nothing was tapped")

    def tap(self, node: Node, action: str, *, system_prompt: bool = False) -> None:
        if not system_prompt:
            self.require_front(action)
        x, y = node.center
        self.adb.shell(f"input tap {x} {y}")

    def swipe_up(self, action: str) -> None:
        self.require_front(action)
        size = re.search(r"(\d+)x(\d+)", self.adb.shell("wm size"))
        width, height = (int(size.group(1)), int(size.group(2))) if size else (1080, 1920)
        x = width // 2
        self.adb.shell(f"input swipe {x} {height * 7 // 10} {x} {height * 3 // 10} 400")

    def back(self) -> None:
        self.require_front("pressing Back")
        self.adb.shell("input keyevent 4")

    def open_url(self, url: str) -> None:
        self.adb.shell(f"am start -W -a android.intent.action.VIEW -d {url} -p {self.package}")

    # Checks ----------------------------------------------------------------

    def step(self, name: str, check) -> None:
        print(f"• {name} …", flush=True)
        check()
        self.passed.append(name)
        print(f"  ✓ {name}", flush=True)

    def launch(self) -> None:
        self.adb.shell(f"monkey -p {self.package} -c android.intent.category.LAUNCHER 1")
        deadline = self.clock() + 60
        while not (self.running() and self.in_front()):
            if self.clock() >= deadline:
                raise SmokeFailure("Acute didn't open within 60 seconds")
            self.sleep(2)

    def first_run(self) -> None:
        for _ in range(FIRST_RUN_STEPS):
            nodes = self.wait_for("the first screen", lambda found: bool(found), timeout=90)
            cancel = self.default_browser_prompt(nodes)
            if cancel is not None:
                self.tap(cancel, "declining Android's default-browser prompt", system_prompt=True)
                self.sleep(3)
                continue
            if self.browser_ready(nodes):
                return
            button = next((find(nodes, text=label) for label in FIRST_RUN_BUTTONS if find(nodes, text=label)), None)
            if button is None:
                self.sleep(3)
                continue
            self.tap(button, f"first-run button '{button.text}'")
            self.sleep(3)
        nodes = self.nodes()
        if not self.browser_ready(nodes):
            labels = ", ".join(node.label() for node in nodes[:25])
            raise SmokeFailure(f"First run didn't reach the home screen. On screen: {labels}")

    @staticmethod
    def browser_ready(nodes: list[Node]) -> bool:
        # An existing profile can reopen its last tab instead of the home screen.
        return bool(find(nodes, label=HOME_TEXT) or find(nodes, description=MENU_DESCRIPTION))

    def https_page(self) -> None:
        self.open_url(HTTPS_PAGE)
        self.wait_for("the HTTPS page to load",
                      lambda nodes: any(find(nodes, label=m, contains=True) for m in HTTPS_PAGE_MARKERS), timeout=90)

    def menu(self) -> None:
        nodes = self.wait_for("the menu button", lambda found: find(found, description=MENU_DESCRIPTION))
        self.tap(find(nodes, description=MENU_DESCRIPTION), "opening the main menu")
        self.wait_for("the main menu", lambda found: find(found, label=MENU_HEADING))
        self.swipe_up("scrolling the main menu")
        self.sleep(2)
        self.swipe_up("scrolling the main menu again")
        self.sleep(2)
        self.require_alive("scrolling the main menu")

    def settings(self) -> None:
        # The menu's last group is headed "Settings" too; the item comes after the heading.
        settings, _ = self.scroll_to(SETTINGS_TEXT, "Settings at the bottom of the main menu", last=True)
        self.tap(settings, "opening Settings")
        self.wait_for("Settings to open", lambda found: find(found, label="General") or find(found, label=PRIVACY_CATEGORY))
        target, seen = self.scroll_to(HTTPS_ONLY_SETTING, f"{PRIVACY_CATEGORY} › {HTTPS_ONLY_SETTING}")
        if PRIVACY_CATEGORY not in seen:
            raise SmokeFailure(f"Settings never showed the {PRIVACY_CATEGORY} group")
        self.tap(target, f"opening {HTTPS_ONLY_SETTING}")
        self.wait_for(f"the {HTTPS_ONLY_SETTING} screen", lambda found: find(found, label=HTTPS_ONLY_SETTING), timeout=30)
        self.require_alive(f"opening {HTTPS_ONLY_SETTING}")
        for _ in range(2):
            self.back()
            self.sleep(2)

    def scroll_to(self, text: str, what: str, attempts: int = 8, last: bool = False) -> tuple[Node, set[str]]:
        """Scroll until `text` is visible; also return every label seen on the way."""
        seen: set[str] = set()
        for _ in range(attempts):
            nodes = self.nodes()
            seen.update(node.label() for node in nodes)
            target = find(nodes, label=text, last=last)
            if target is not None:
                return target, seen
            self.swipe_up(f"scrolling to {what}")
            self.sleep(2)
        raise SmokeFailure(f"Couldn't find {what} in Settings")

    def report_issue(self) -> None:
        """Check the local opt-in/review/cancel flow; never tap Open GitHub draft."""
        self.open_url(HTTPS_PAGE)
        self.wait_for("browser controls", self.browser_ready)
        self.menu()
        settings, _ = self.scroll_to(SETTINGS_TEXT, "Settings in the menu", last=True)
        self.tap(settings, "opening Settings for issue review")
        self.wait_for("Settings", lambda nodes: find(nodes, label="General"))
        entry, _ = self.scroll_to("Report an issue", "Report an issue")
        self.tap(entry, "opening local issue options")
        def dialog_label(nodes, label):
            return next((node for node in nodes if node.label().casefold() == label.casefold()), None)
        nodes = self.wait_for("local crash opt-in", lambda nodes: dialog_label(nodes, "Include last crash"))
        include = dialog_label(nodes, "Include last crash")
        if include.checked is not False:
            raise SmokeFailure("Include last crash must be explicitly unchecked by default")
        review = dialog_label(nodes, "Review issue draft")
        if review is None:
            raise SmokeFailure("Local issue options have no review action")
        self.tap(review, "reviewing the issue draft")
        nodes = self.wait_for("editable issue draft", lambda nodes: dialog_label(nodes, "Open GitHub draft"))
        draft = find(nodes, text="What happened?", contains=True)
        if draft is None or "Acute Web local Java/Kotlin crash" in draft.text:
            raise SmokeFailure("Unchecked crash details must not be included in the draft")
        cancel = dialog_label(nodes, "Cancel")
        if cancel is None:
            raise SmokeFailure("Issue preview has no Cancel action")
        self.tap(cancel, "canceling without opening GitHub")
        self.wait_for("Settings after cancel", lambda nodes: find(nodes, label="Report an issue"))
        self.back()

    def http_page(self) -> None:
        self.open_url(HTTP_ONLY_PAGE)
        self.wait_for("the HTTPS-Only warning page",
                      lambda nodes: any(HTTPS_ONLY_ERROR.lower() in node.label().lower() for node in nodes), timeout=90)

    def finish(self) -> None:
        self.require_alive("the final check")

    # Evidence --------------------------------------------------------------

    def save_evidence(self, name: str) -> None:
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output / f"{name}.png").write_bytes(self.adb.pull_bytes("exec-out", "screencap", "-p"))
        try:
            self.adb.shell("uiautomator dump /sdcard/acute-smoke.xml", check=False)
            (self.output / f"{name}-screen.xml").write_text(self.adb.shell("cat /sdcard/acute-smoke.xml", check=False),
                                                            encoding="utf-8")
        except Exception:  # Evidence is best effort; the original failure matters more.
            pass
        (self.output / f"{name}-logcat.txt").write_text(self.adb.run("logcat", "-d", "-t", "2000", check=False),
                                                       encoding="utf-8")


def run(adb: Adb, package: str, output: Path, *, apk: Path | None, fresh: bool,
        sleep=time.sleep, clock=time.monotonic) -> int:
    smoke = Smoke(adb, package, output, sleep=sleep, clock=clock)
    adb.run("wait-for-device", timeout=300)
    if apk is not None:
        adb.run("install", "-r", str(apk), timeout=300)
    if fresh:
        adb.shell(f"pm clear {package}")
    adb.run("logcat", "-b", "crash", "-c", check=False)
    checks = [
        ("Launch", smoke.launch),
        ("First run reaches the home screen", smoke.first_run),
        ("HTTPS page loads", smoke.https_page),
        ("Main menu opens and scrolls on a web page", smoke.menu),
        (f"Settings › {PRIVACY_CATEGORY} › {HTTPS_ONLY_SETTING}", smoke.settings),
        ("Issue draft is opt-in and can be canceled locally", smoke.report_issue),
        ("HTTP-only site shows the HTTPS-Only warning", smoke.http_page),
        ("No crash and still running", smoke.finish),
    ]
    try:
        for name, check in checks:
            smoke.step(name, check)
    except SmokeFailure as failure:
        print(f"\n✗ {failure}", file=sys.stderr, flush=True)
        smoke.save_evidence("failure")
        return 1
    smoke.save_evidence("final")
    print(f"\nAll {len(smoke.passed)} smoke checks passed for {package}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to a legacy code page that can't print ✓ or •.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--package", default="com.acuteweb.browser.dev")
    parser.add_argument("--apk", type=Path, help="install this APK first")
    parser.add_argument("--fresh", action="store_true",
                        help="clear the app's data first so first run is tested (erases its profile)")
    parser.add_argument("--serial", help="adb device serial when several are connected")
    parser.add_argument("--out", type=Path, default=Path("smoke-output"))
    args = parser.parse_args(argv)
    return run(Adb(args.serial), args.package, args.out, apk=args.apk, fresh=args.fresh)


if __name__ == "__main__":
    sys.exit(main())
