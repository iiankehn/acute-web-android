"""Release provenance must reject real Git histories from the wrong channel."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from shell_support import bash_executable

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify_release_ref.sh'


@unittest.skipUnless(shutil.which('bash') and shutil.which('git'), 'Requires Bash and Git')
class ReleaseRefTests(unittest.TestCase):
    def test_channel_ancestry_and_checkout_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
            git('init', '-b', 'main')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Test')
            git('commit', '--allow-empty', '-m', 'stable')
            git('tag', 'v1.0.0')
            git('checkout', '-b', 'beta')
            git('commit', '--allow-empty', '-m', 'beta')
            git('tag', '-a', 'v2.0.0-beta.1', '-m', 'annotated beta')
            git('checkout', '-b', 'dev')
            git('commit', '--allow-empty', '-m', 'unreviewed dev')
            for tag in ('v9.0.0', 'v9.0.0-beta.1', 'vgarbage'):
                git('tag', tag)
            git('remote', 'add', 'origin', str(root))
            def verify(tag, checkout=True):
                if checkout:
                    git('checkout', '--detach', tag)
                env = dict(os.environ, GITHUB_REF=f'refs/tags/{tag}')
                return subprocess.run([bash_executable(), SCRIPT.as_posix()], cwd=root, env=env, capture_output=True, text=True)
            for tag in ('v1.0.0', 'v2.0.0-beta.1'):
                result = verify(tag)
                self.assertEqual(result.returncode, 0, result.stderr)
            for tag in ('v9.0.0', 'v9.0.0-beta.1', 'vgarbage'):
                self.assertNotEqual(verify(tag).returncode, 0)
            # Even a valid tag must not authorize signing a different checkout.
            git('checkout', '--detach', 'dev')
            self.assertNotEqual(verify('v1.0.0', checkout=False).returncode, 0)
            git('branch', '-D', 'beta')
            self.assertNotEqual(verify('v2.0.0-beta.1').returncode, 0)
