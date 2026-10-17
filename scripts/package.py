#!/usr/bin/env python3
"""Create a source bundle while excluding generated and secret files."""

from pathlib import Path
import os
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "acute-web-android.zip"

EXCLUDED_PARTS = {".git", ".idea", ".gradle", "__pycache__", "dist", "firefox", ".aws", ".ssh"}
EXCLUDED_SUFFIXES = {".jks", ".keystore", ".pyc", ".apk", ".aab", ".pem", ".key", ".p12", ".pfx"}


def package_source(root: Path, output: Path) -> None:
    """Bundle tracked working files only; never traverse local secrets or symlinks."""
    root = root.resolve()
    names = subprocess.check_output(["git", "-C", str(root), "ls-files", "--cached", "-z"])
    paths = []
    for name in sorted(set(names.split(b"\0")) - {b""}):
        relative = Path(os.fsdecode(name))
        if (any(part.lower() in EXCLUDED_PARTS for part in relative.parts)
                or relative.suffix.lower() in EXCLUDED_SUFFIXES
                or relative.name.lower() == ".env" or relative.name.lower().startswith(".env.")):
            continue
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Refusing source link outside the archive boundary: {relative}")
        if not path.is_file():
            raise ValueError(f"Tracked source is missing or not a regular file: {relative}")
        paths.append((path, relative))
    if not paths:
        raise ValueError("No tracked source files to package")
    output = output.resolve()
    if any(path.resolve() == output for path, _ in paths):
        raise ValueError("Source bundle cannot overwrite a tracked source file")
    # Publish only a complete archive; keep an existing bundle on failure.
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, relative in paths:
                archive.write(path, Path(root.name) / relative)
        temporary_path.replace(output)
    finally:
        temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    package_source(ROOT, OUTPUT)
    print(OUTPUT)
