import io
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_apk_native import MACHINES, REQUIRED, verify
from apply_overlay import patch_gradle, OverlayError
from test_overlay import GRADLE


def elf(machine):
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", header, 18, machine)
    return header


def apk(libraries):
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as archive:
        for path, content in libraries.items():
            archive.writestr(path, content)
    result.seek(0)
    return result


class NativeApkTests(unittest.TestCase):
    def test_overlay_filters_dependencies_and_splits_together(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "build.gradle"
            path.write_text(GRADLE)
            patch_gradle(path)
            text = path.read_text()
            self.assertIn('System.getenv("ACUTE_TARGET_ABI")', text)
            self.assertIn('throw new GradleException', text)
            self.assertIn('packaging.jniLibs.excludes +=', text)
            self.assertIn('.findAll { it != acuteTargetAbi }', text)
            self.assertIn('include acuteTargetAbi', text)
            self.assertNotIn('include "armeabi-v7a", "arm64-v8a", "x86_64"', text)

    def test_changed_upstream_split_configuration_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "build.gradle"
            path.write_text(GRADLE.replace('include "armeabi-v7a", "arm64-v8a", "x86_64"', 'include "new-abi"'))
            with self.assertRaises(OverlayError):
                patch_gradle(path)

    def libraries(self, abi):
        return {f"lib/{abi}/{name}": elf(MACHINES[abi]) for name in REQUIRED}

    def test_complete_native_packages(self):
        for abi in MACHINES:
            with self.subTest(abi=abi):
                self.assertEqual(verify(apk(self.libraries(abi)), abi), len(REQUIRED))

    def test_partial_foreign_abi_cannot_advertise_compatibility(self):
        libraries = self.libraries("arm64-v8a")
        libraries["lib/x86_64/libjnidispatch.so"] = elf(62)
        with self.assertRaisesRegex(ValueError, "Foreign"):
            verify(apk(libraries), "arm64-v8a")

    def test_missing_engine_is_rejected(self):
        libraries = self.libraries("x86_64")
        del libraries["lib/x86_64/libxul.so"]
        with self.assertRaisesRegex(ValueError, "Missing.*libxul"):
            verify(apk(libraries), "x86_64")

    def test_relabelled_arm_library_is_rejected(self):
        libraries = self.libraries("x86_64")
        libraries["lib/x86_64/libxul.so"] = elf(183)
        with self.assertRaisesRegex(ValueError, "Wrong ELF"):
            verify(apk(libraries), "x86_64")

    def test_empty_apk_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing"):
            verify(apk({}), "x86_64")
