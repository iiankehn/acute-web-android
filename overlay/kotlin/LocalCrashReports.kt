package org.mozilla.fenix.acute

import android.content.Context
import android.os.Build
import android.os.Process
import android.util.AtomicFile
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

/** One bounded, sanitized main-process Java/Kotlin crash. Never uploads or logs it. */
object LocalCrashReports {
    private val installed = AtomicBoolean(false)
    private val handling = AtomicBoolean(false)

    private fun file(context: Context) = AtomicFile(File(context.noBackupFilesDir, "acute-last-crash.txt"))

    fun install(context: Context) {
        if (!installed.compareAndSet(false, true)) return
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, crash ->
            try {
                if (handling.compareAndSet(false, true)) {
                    val report = CrashReportSanitizer.format(
                        crash, context.packageManager.getPackageInfo(context.packageName, 0).versionName,
                        Build.VERSION.RELEASE, Build.MODEL,
                    )
                    val target = file(context)
                    val output = target.startWrite()
                    try {
                        output.write(report.toByteArray(Charsets.UTF_8))
                        target.finishWrite(output)
                    } catch (failure: Throwable) {
                        target.failWrite(output)
                    }
                }
            } catch (_: Throwable) {
                // A full disk or low-memory crash must still reach Android's original handler.
            } finally {
                if (previous != null) {
                    previous.uncaughtException(thread, crash)
                } else {
                    Process.killProcess(Process.myPid())
                }
            }
        }
    }

    fun read(context: Context): String? = try {
        file(context).openRead().use { input ->
            // Reject unexpectedly large files instead of reading arbitrary diagnostics.
            val bytes = ByteArray(16001)
            var count = 0
            while (count < bytes.size) {
                val read = input.read(bytes, count, bytes.size - count)
                if (read < 0) break
                count += read
            }
            if (count > 16000) null else String(bytes, 0, count, Charsets.UTF_8)
        }
    } catch (_: Exception) {
        null
    }

    fun delete(context: Context) = file(context).delete()
}
