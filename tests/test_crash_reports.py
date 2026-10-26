"""Execute the production diagnostics allowlist on the JVM, without Android mocks."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CrashReportTests(unittest.TestCase):
    def test_sensitive_messages_cycles_frames_and_size(self):
        harness = r'''
import org.mozilla.fenix.acute.CrashReportSanitizer;
public class CrashReportTest {
    private static void check(boolean value) {
        if (!value) throw new AssertionError("Crash report privacy/bounds regression");
    }
    public static void main(String[] args) {
        RuntimeException error = new RuntimeException("https://secret.test/?token=ACCOUNT_SECRET");
        RuntimeException cause = new RuntimeException("password=PASSWORD_SECRET");
        error.initCause(cause);
        cause.initCause(error);
        error.addSuppressed(new RuntimeException("SUPPRESSED_SECRET"));
        StackTraceElement frame = new StackTraceElement("org.mozilla.Example", "openPage", "/private/FILE_SECRET", 42);
        error.setStackTrace(new StackTraceElement[] {frame});
        cause.setStackTrace(new StackTraceElement[] {new StackTraceElement("https://HOST_SECRET", "token=METHOD_SECRET", "FILE_SECRET", 9)});
        String result = CrashReportSanitizer.format(error, "2.0.0-dev.147", "12", "Pixel 3 XL");
        check(result.contains("Version: 2.0.0-dev.147"));
        check(result.contains("Android: 12") && result.contains("Model: Pixel 3 XL"));
        check(result.contains("java.lang.RuntimeException"));
        check(result.contains("org.mozilla.Example.openPage (line 42)"));
        check(result.contains("Caused by:"));
        check(!result.contains("SECRET") && !result.contains("https://"));
        check(result.split("Exception:", -1).length == 2);
        StackTraceElement[] huge = new StackTraceElement[10000];
        java.util.Arrays.fill(huge, new StackTraceElement("a".repeat(160), "b".repeat(160), "ignored", 10));
        error.setStackTrace(huge);
        check(CrashReportSanitizer.format(error, "v", "12", "model").length() <= 4000);
        java.util.Arrays.fill(huge, frame);
        error.setStackTrace(huge);
        result = CrashReportSanitizer.format(error, "v", "12", "model");
        check(result.split("openPage", -1).length == 13);
        check(CrashReportSanitizer.format(null, "https://PRIVATE", "12", "user@PRIVATE").contains("[omitted]"));
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CrashReportTest.java"
            path.write_text(harness, encoding="utf-8")
            subprocess.run(["java", "com.sun.tools.javac.Main", "-d", directory,
                            str(ROOT / "overlay/java/CrashReportSanitizer.java"), str(path)], check=True)
            subprocess.run(["java", "-cp", directory, "CrashReportTest"], check=True, timeout=20)
