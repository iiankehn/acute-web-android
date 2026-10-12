from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_upstream_overlay import fetch_source

class UpstreamFetchTests(unittest.TestCase):
    def test_sparse_snapshot_matches_commit_and_excludes_unneeded_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
            (repo / "needed").mkdir()
            (repo / "needed/file.txt").write_text("immutable source\n")
            (repo / "unused.txt").write_text("must not enter overlay snapshot\n")
            git("add", ".")
            git("-c", "user.name=Acute Test", "-c", "user.email=acute-test@example.invalid", "commit", "--quiet", "-m", "Fixture")
            ref = git("rev-parse", "HEAD")
            snapshot = root / "snapshot"
            fetch_source(snapshot, str(repo), ref, ["needed/file.txt"])
            self.assertEqual((snapshot / "needed/file.txt").read_text(), "immutable source\n")
            self.assertFalse((snapshot / "unused.txt").exists())
            with self.assertRaisesRegex(ValueError, "incomplete"):
                fetch_source(root / "missing", str(repo), ref, ["absent.txt"])

    def test_ref_must_be_immutable_before_network_access(self):
        with self.assertRaises(ValueError):
            fetch_source(Path("unused"), "unused", "main", ["mach"])
