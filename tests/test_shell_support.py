from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from shell_support import bash_executable


class ShellSelectionTests(unittest.TestCase):
    def test_windows_git_layouts_select_git_bash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Git"
            bash = root / "bin/bash.exe"
            bash.parent.mkdir(parents=True)
            bash.touch()
            for relative in ("cmd/git.exe", "bin/git.exe", "mingw64/bin/git.exe"):
                git = root / relative
                git.parent.mkdir(parents=True, exist_ok=True)
                git.touch()
                with patch("shell_support.os", SimpleNamespace(name="nt")), patch("shell_support.shutil.which", return_value=str(git)):
                    self.assertTrue(Path(bash_executable()).samefile(bash))

    def test_windows_without_git_bash_fails_instead_of_using_wsl(self):
        with patch("shell_support.os", SimpleNamespace(name="nt")), patch("shell_support.shutil.which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "Git Bash"):
                bash_executable()
