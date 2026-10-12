/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

import org.junit.Assert.*
import org.junit.Test
import java.io.*
import java.util.concurrent.atomic.AtomicBoolean

class DownloadPolicyTest {
    @Test fun namesStripPathsControlsAndSpoofingCharacters() {
        assertEquals("report.pdf", DownloadPolicy.filename("../../secret/\u202ereport.pdf\n"))
        assertEquals("file.txt", DownloadPolicy.filename("C:\\path\\file.txt"))
        assertEquals("download.bin", DownloadPolicy.filename(".."))
        assertEquals(120, DownloadPolicy.filename("a".repeat(500)).length)
        assertEquals("application/octet-stream", DownloadPolicy.mime("bad\r\nheader"))
        assertEquals("text/plain", DownloadPolicy.mime("TEXT/PLAIN; charset=utf-8"))
    }
    @Test fun streamsWithBoundedReadsAndClosesBothResources() {
        val bytes = ByteArray(150_000) { (it % 251).toByte() }
        val inputClosed = AtomicBoolean(); val outputClosed = AtomicBoolean()
        val input = object : ByteArrayInputStream(bytes) {
            override fun read(b: ByteArray, off: Int, len: Int): Int { assertTrue(len <= 32768); return super.read(b, off, len) }
            override fun close() { inputClosed.set(true) }
        }
        val output = object : ByteArrayOutputStream() { override fun close() { outputClosed.set(true) } }
        assertEquals(bytes.size.toLong(), DownloadPolicy.copy(input, output, bytes.size.toLong()))
        assertArrayEquals(bytes, output.toByteArray()); assertTrue(inputClosed.get()); assertTrue(outputClosed.get())
    }
    @Test fun cancellationAndWriteFailureCloseResourcesWithoutReportingSuccess() {
        val closed = AtomicBoolean()
        val input = object : ByteArrayInputStream(ByteArray(100_000)) { override fun close() { closed.set(true) } }
        val cancelled = AtomicBoolean()
        try { DownloadPolicy.copy(input, ByteArrayOutputStream(), cancelled = cancelled::get, progress = { cancelled.set(true) }); fail("Cancellation ignored") }
        catch (_: InterruptedIOException) { }
        assertTrue(closed.get())
        closed.set(false)
        val failure = object : OutputStream() { override fun write(value: Int) { throw IOException("Destination failed") }; override fun close() { closed.set(true) } }
        try { DownloadPolicy.copy(ByteArrayInputStream(byteArrayOf(1)), failure); fail("Write failure ignored") }
        catch (_: IOException) { }
        assertTrue(closed.get())
    }
    @Test fun rejectsTruncatedBodiesAndOversizedDeclarations() {
        try { DownloadPolicy.copy(ByteArrayInputStream(byteArrayOf(1)), ByteArrayOutputStream(), 2); fail("Truncated response accepted") }
        catch (_: IOException) { }
        try { DownloadPolicy.copy(ByteArrayInputStream(byteArrayOf()), ByteArrayOutputStream(), DownloadPolicy.MAX_BYTES + 1); fail("Oversized response accepted") }
        catch (_: IllegalArgumentException) { }
    }
}
