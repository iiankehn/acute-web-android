import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/build-android.yml'


@unittest.skipUnless(shutil.which('bash'), 'Workflow policy execution requires Bash')
class SigningShellPolicyTests(unittest.TestCase):
    def run_policy(self, kind, content):
        text = WORKFLOW.read_text(encoding='utf-8')
        script = text.split(f'# BEGIN signed APK {kind} policy\n', 1)[1].split(f'# END signed APK {kind} policy', 1)[0]
        script = textwrap.dedent(script)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dist').mkdir()
            report = root / ('acute-unsigned-badging.txt' if kind == 'debug' else 'dist/manifest-permissions-arm64-v8a.txt')
            if content is not None:
                report.write_text(content, encoding='utf-8')
            env = dict(os.environ, RUNNER_TEMP=directory, ABI='arm64-v8a')
            return subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], cwd=root, env=env, capture_output=True)

    def test_debuggable_and_missing_reports_block_signing(self):
        self.assertEqual(self.run_policy('debug', "package: name='com.acuteweb.browser.dev'\n").returncode, 0)
        for content in ('application-debuggable\n', None):
            with self.subTest(content=content):
                self.assertNotEqual(self.run_policy('debug', content).returncode, 0)

    def test_each_prohibited_permission_and_read_failure_blocks_release(self):
        self.assertEqual(self.run_policy('permission', 'uses-permission: android.permission.INTERNET\n').returncode, 0)
        for name in ('com.adjust.preinstall.READ_PERMISSION', 'com.google.android.gms.permission.AD_ID',
                     'android.permission.QUERY_ALL_PACKAGES', 'android.permission.REQUEST_DELETE_PACKAGES',
                     'android.permission.REQUEST_INSTALL_PACKAGES', None):
            with self.subTest(name=name):
                content = f'uses-permission: {name}\n' if name else None
                self.assertNotEqual(self.run_policy('permission', content).returncode, 0)
