from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from scripts.package import package_source


class SourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        self.output = Path(self.temp.name) / "source.zip"
        self.git("init", "--quiet")
        (self.root / "app.py").write_text("print('source')\n")
        self.git("add", "app.py")

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def test_excludes_untracked_local_data_and_tracked_credentials(self):
        (self.root / "local-notes.txt").write_text("private notes")
        for name in (".env", ".env.production", "signing.JKS", "private.pem", "output.apk"):
            (self.root / name).write_text("not source")
            self.git("add", name)
        package_source(self.root, self.output)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), ["source/app.py"])
            self.assertEqual(archive.read("source/app.py"), (self.root / "app.py").read_bytes())

    def test_missing_source_preserves_existing_bundle(self):
        self.output.write_bytes(b"previous bundle")
        (self.root / "app.py").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            package_source(self.root, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous bundle")

    def test_output_cannot_replace_source(self):
        with self.assertRaisesRegex(ValueError, "overwrite"):
            package_source(self.root, self.root / "app.py")

    def test_external_symlink_is_rejected(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("external data")
        link = self.root / "linked.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Creating symlinks requires OS privileges")
        self.git("add", "linked.txt")
        with self.assertRaisesRegex(ValueError, "link"):
            package_source(self.root, self.output)
