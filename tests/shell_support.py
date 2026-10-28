"""Select a real shell for policy tests; Windows' system bash is a WSL stub."""
import os
from pathlib import Path
import shutil


def bash_executable():
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            # Git for Windows exposes git.exe from cmd/ or bin/.
            candidate = Path(git).resolve().parent.parent / "bin/bash.exe"
            if candidate.is_file():
                return str(candidate)
        raise FileNotFoundError("Git Bash is required for Windows shell-policy tests")
    shell = shutil.which("bash")
    if not shell:
        raise FileNotFoundError("Bash is required for shell-policy tests")
    return shell
