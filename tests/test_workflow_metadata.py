"""Execute the actual metadata shell step without credentials or a GitHub runner."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkflowMetadataTests(unittest.TestCase):
    def run_metadata(self, ref, event="push", manual=""):
        workflow = (ROOT / ".github/workflows/build-android.yml").read_text()
        start = workflow.index("        run: |", workflow.index("        id: version"))
        end = workflow.index("\n  provenance:", start)
        script = "\n".join(line[10:] for line in workflow[start:end].splitlines()[1:])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            env = dict(os.environ, GITHUB_REF=ref, GITHUB_REF_NAME=ref.split("/")[-1],
                       GITHUB_EVENT_NAME=event, GITHUB_RUN_NUMBER="501", GITHUB_OUTPUT=str(output),
                       PINNED_FIREFOX_REF="3c71aeacdb296402e41fb2084b13e797d1770642", MANUAL_FIREFOX_REF=manual)
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script], env=env, capture_output=True, text=True)
            values = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
            return result, values

    def test_channel_selection_and_unsigned_dev_build(self):
        for ref, package, channel, version in (
            ("refs/heads/dev", "com.acuteweb.browser.dev", "dev", "2.0.0-dev.501"),
            ("refs/heads/beta", "com.acuteweb.browser.beta", "beta", "2.0.0-beta.1"),
            ("refs/tags/v1.1.2", "com.acuteweb.browser", "stable", "1.1.2"),
            ("refs/tags/v2.0.0-beta.2", "com.acuteweb.browser.beta", "beta", "2.0.0-beta.2"),
        ):
            with self.subTest(ref=ref):
                result, values = self.run_metadata(ref)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values["package"], package)
                self.assertEqual(values["channel"], channel)
                self.assertEqual(values["version"], version)
                if channel == "dev":
                    self.assertEqual(values["task"], "fenix:assembleRelease")
                    self.assertEqual(values["gradle_flags"], "-PlocalProperties.disableDebugSigning=true")

    def test_rejects_malformed_release_tags_and_mutable_manual_source(self):
        result, values = self.run_metadata("refs/pull/6/merge", "pull_request")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values["channel"], "dev")
        self.assertEqual(values["package"], "com.acuteweb.browser.dev")
        self.assertEqual(values["task"], "fenix:assembleRelease")
        self.assertEqual(values["gradle_flags"], "-PlocalProperties.disableDebugSigning=true")
        for ref in ("refs/tags/v2.0.0-dev.1", "refs/tags/vgarbage"):
            self.assertNotEqual(self.run_metadata(ref)[0].returncode, 0)
        self.assertNotEqual(self.run_metadata("refs/heads/dev", "workflow_dispatch", "main")[0].returncode, 0)
