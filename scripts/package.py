#!/usr/bin/env python3
"""Create a source bundle while excluding generated and secret files."""

from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "acute-web-android.zip"

EXCLUDED_PARTS = {".git", ".idea", ".gradle", "__pycache__", "dist", "firefox"}
EXCLUDED_SUFFIXES = {".jks", ".keystore", ".pyc"}

if OUTPUT.exists():
    OUTPUT.unlink()
with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if path.is_dir() or any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        archive.write(path, Path(ROOT.name) / relative)
print(OUTPUT)
