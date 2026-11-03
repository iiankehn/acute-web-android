package org.mozilla.fenix.acute;

import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Set;

/** Diagnostics allowlist: never calls Throwable.toString/getMessage/printStackTrace. */
public final class CrashReportSanitizer {
    private CrashReportSanitizer() {}

    private static String metadata(String value) {
        if (value == null || value.length() > 80 || !value.matches("[A-Za-z0-9 ._()+-]+")) {
            return "[omitted]";
        }
        return value;
    }

    private static String symbol(String value) {
        if (value == null || value.length() > 160 || !value.matches("[A-Za-z_$][A-Za-z0-9_.$<>-]*")) {
            return "[omitted]";
        }
        return value;
    }

    public static String format(Throwable crash, String version, String android, String model) {
        StringBuilder out = new StringBuilder("Acute Web local Java/Kotlin crash\n");
        out.append("Version: ").append(metadata(version)).append('\n');
        out.append("Android: ").append(metadata(android)).append('\n');
        out.append("Model: ").append(metadata(model)).append('\n');
        out.append("Messages, filenames, thread names and suppressed exceptions omitted.\n");
        Set<Throwable> seen = Collections.newSetFromMap(new IdentityHashMap<Throwable, Boolean>());
        for (int causes = 0; crash != null && causes < 3 && seen.add(crash); causes++) {
            out.append(causes == 0 ? "Exception: " : "Caused by: ").append(symbol(crash.getClass().getName())).append('\n');
            StackTraceElement[] frames = crash.getStackTrace();
            for (int i = 0; i < Math.min(frames.length, 12); i++) {
                StackTraceElement frame = frames[i];
                String line = "  at " + symbol(frame.getClassName()) + "." + symbol(frame.getMethodName())
                    + " (line " + frame.getLineNumber() + ")\n";
                if (out.length() + line.length() > 4000) return out.toString();
                out.append(line);
            }
            crash = crash.getCause();
        }
        return out.substring(0, Math.min(4000, out.length()));
    }
}
