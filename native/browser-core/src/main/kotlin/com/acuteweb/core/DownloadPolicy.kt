/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

import java.io.InputStream
import java.io.OutputStream
import java.io.IOException
import java.io.InterruptedIOException

object DownloadPolicy {
    const val MAX_BYTES = 2_147_483_648L
    fun filename(suggestion: String): String {
        val leaf = suggestion.substringAfterLast('/').substringAfterLast('\\')
        return leaf.filter { !it.isISOControl() && Character.getType(it) != Character.FORMAT.toInt() }
            .trim().trim('.').take(120).ifEmpty { "download.bin" }
    }
    fun mime(value: String?): String = value?.substringBefore(';')?.trim()
        ?.takeIf { it.length <= 128 && it.matches(Regex("[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+")) }
        ?.lowercase(java.util.Locale.ROOT) ?: "application/octet-stream"

    /** Fixed memory use, resource ownership, cancellation and truncated-body rejection. */
    fun copy(source: InputStream, destination: OutputStream, expected: Long? = null,
             cancelled: () -> Boolean = { false }, progress: (Long) -> Unit = {}): Long = source.use { input ->
        destination.use { output ->
            require(expected == null || expected in 0..MAX_BYTES)
            val buffer = ByteArray(32 * 1024)
            var count = 0L
            while (true) {
                if (cancelled()) throw InterruptedIOException("Download cancelled")
                val read = input.read(buffer)
                if (read < 0) break
                if (read == 0) continue
                if (cancelled()) throw InterruptedIOException("Download cancelled")
                if (count + read > MAX_BYTES || (expected != null && count + read > expected)) throw IOException("Download exceeds its declared limit")
                output.write(buffer, 0, read); count += read; progress(count)
            }
            if (cancelled()) throw InterruptedIOException("Download cancelled")
            if (expected != null && count != expected) throw IOException("Download was interrupted")
            output.flush(); count
        }
    }
}
