/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.content.ContentValues
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import android.view.WindowManager
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.acuteweb.core.BrowsingMode
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.mozilla.geckoview.WebResponse
import java.io.ByteArrayInputStream
import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean

/** Destinations are unique app-owned MediaStore fixtures on the disposable emulator. */
private fun destination(): Uri = app.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, ContentValues().apply {
    put(MediaStore.MediaColumns.DISPLAY_NAME, "acute-fixture-${UUID.randomUUID()}.bin")
    put(MediaStore.MediaColumns.MIME_TYPE, "application/octet-stream")
    put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/AcuteFixtures")
    put(MediaStore.MediaColumns.IS_PENDING, 1)
}) ?: error("No fixture destination")
private fun contents(uri: Uri) = app.contentResolver.openInputStream(uri)!!.use { it.readBytes() }
private class TrackedBody(bytes: ByteArray) : ByteArrayInputStream(bytes) {
    val closed = AtomicBoolean(false)
    override fun close() { closed.set(true); super.close() }
}
private fun response(body: TrackedBody, length: Long = body.available().toLong()): WebResponse {
    val builder = WebResponse.Builder("https://example.com/download").statusCode(200).body(body)
    builder.header("Content-Type", "application/octet-stream"); builder.header("Content-Length", length.toString())
    builder.header("Content-Disposition", "attachment; filename=fixture.bin")
    return builder.build()
}
@RunWith(AndroidJUnit4::class)
class DownloadDeviceTest {
    @Test fun actualGeckoAuthenticatedDownloadSavesExactBytesWithoutRefetch() {
        val manager = DownloadController(app); val uri = destination()
        try {
            TestSite().use { site ->
                SessionDriver(downloadResponse = manager::receive).use { browser ->
                    browser.open(); val token = UUID.randomUUID().toString()
                    assertEquals("marker=normal", browser.load(site.uri("/normal-set", token), token))
                    onMain { browser.engine.navigate(site.uri("/download-auth")) }
                    eventually { fromMain { manager.offer != null } }
                    onMain { assertTrue(manager.choose(manager.offer!!.id)); assertTrue(manager.finishPicker(uri)) }
                    eventually { fromMain { manager.visible(BrowsingMode.NORMAL).single().status == DownloadController.Status.COMPLETE } }
                    assertArrayEquals(site.downloadBytes, contents(uri))
                    assertEquals(1, site.downloadRequests.get())
                }
            }
        } finally { onMain { manager.shutdown() }; app.contentResolver.delete(uri, null, null) }
    }
    @Test fun cancelledPickerCannotWriteItsResultToANewerRequest() {
        val manager = DownloadController(app); val uri = destination()
        val first = TrackedBody(byteArrayOf(1)); val refused = TrackedBody(byteArrayOf(2)); val next = TrackedBody(byteArrayOf(3))
        try {
            onMain {
                assertTrue(manager.receive(BrowsingMode.NORMAL, response(first)))
                val id = manager.offer!!.id; assertTrue(manager.choose(id)); manager.cancel(id)
                assertTrue(first.closed.get())
                assertFalse(manager.receive(BrowsingMode.NORMAL, response(refused)))
                assertTrue(refused.closed.get())
                assertFalse(manager.finishPicker(uri))
                assertTrue(manager.receive(BrowsingMode.NORMAL, response(next)))
            }
            assertArrayEquals(byteArrayOf(), contents(uri))
        } finally { onMain { manager.shutdown() }; app.contentResolver.delete(uri, null, null) }
        assertTrue(next.closed.get())
    }
    @Test fun truncatedAndUnwritableDestinationsFailAndCloseStreams() {
        val manager = DownloadController(app); val uri = destination()
        val truncated = TrackedBody(byteArrayOf(1))
        try {
            onMain { manager.receive(BrowsingMode.NORMAL, response(truncated, 10)); manager.choose(manager.offer!!.id); manager.finishPicker(uri) }
            eventually { fromMain { manager.visible(BrowsingMode.NORMAL).first().status == DownloadController.Status.FAILED } }
            assertTrue(truncated.closed.get())
            val missing = TrackedBody(byteArrayOf(2))
            onMain { manager.receive(BrowsingMode.NORMAL, response(missing)); manager.choose(manager.offer!!.id); manager.finishPicker(Uri.parse("content://com.acuteweb.missing-provider/file")) }
            eventually { fromMain { manager.visible(BrowsingMode.NORMAL).first().status == DownloadController.Status.FAILED } }
            assertTrue(missing.closed.get()); assertArrayEquals(byteArrayOf(1), contents(uri))
        } finally { onMain { manager.shutdown() }; app.contentResolver.delete(uri, null, null) }
    }
    @Test fun privateMetadataClearsButExplicitlySavedFileRemains() {
        val manager = DownloadController(app); val uri = destination(); val bytes = byteArrayOf(7, 8, 9)
        val body = TrackedBody(bytes)
        try {
            onMain { manager.receive(BrowsingMode.PRIVATE, response(body)); manager.choose(manager.offer!!.id); manager.finishPicker(uri) }
            eventually { fromMain { manager.visible(BrowsingMode.PRIVATE).single().status == DownloadController.Status.COMPLETE } }
            onMain { assertTrue(manager.visible(BrowsingMode.NORMAL).isEmpty()); manager.forgetPrivate(); assertTrue(manager.visible(BrowsingMode.PRIVATE).isEmpty()) }
            assertArrayEquals(bytes, contents(uri)); assertTrue(body.closed.get())
        } finally { onMain { manager.shutdown() }; app.contentResolver.delete(uri, null, null) }
    }
    @Test fun closingPrivateWindowCancelsAnActiveTransferAndDiscardsItsMetadata() {
        val manager = DownloadController(app); val uri = destination()
        val waiting = java.util.concurrent.CountDownLatch(1)
        val released = java.util.concurrent.CountDownLatch(1)
        val closed = AtomicBoolean(false)
        val reads = java.util.concurrent.atomic.AtomicInteger(0)
        val body = object : java.io.InputStream() {
            override fun read(): Int = error("Use bounded reads")
            override fun read(bytes: ByteArray, offset: Int, length: Int): Int {
                if (reads.getAndIncrement() == 0) { java.util.Arrays.fill(bytes, offset, offset + 8192, 42.toByte()); return 8192 }
                waiting.countDown()
                if (!released.await(60, java.util.concurrent.TimeUnit.SECONDS)) throw java.io.IOException("Fixture timed out")
                throw java.io.IOException("Closed")
            }
            override fun close() { closed.set(true); released.countDown() }
        }
        try {
            onMain {
                val response = WebResponse.Builder("https://example.com/private-download").statusCode(200).body(body).build()
                assertTrue(manager.receive(BrowsingMode.PRIVATE, response)); manager.choose(manager.offer!!.id); manager.finishPicker(uri)
            }
            assertTrue(waiting.await(20, java.util.concurrent.TimeUnit.SECONDS))
            onMain { manager.forgetPrivate(); assertTrue(manager.visible(BrowsingMode.PRIVATE).isEmpty()) }
            eventually { closed.get() && fromMain { !manager.busy } }
            assertTrue(fromMain { manager.visible(BrowsingMode.NORMAL).isEmpty() })
            assertEquals(8192, contents(uri).size)
        } finally { released.countDown(); onMain { manager.shutdown() }; app.contentResolver.delete(uri, null, null) }
    }
    @Test fun privatePromptRequiresExplicitSaveAndClosesWithThePrivateWindow() {
        val body = TrackedBody(byteArrayOf(4, 5))
        ActivityScenario.launch(BrowserActivity::class.java).use { scenario ->
            eventually { fromMain { app.browser.ready } }
            scenario.onActivity {
                app.browser.newTab(BrowsingMode.PRIVATE)
                assertTrue(app.downloads.receive(BrowsingMode.PRIVATE, response(body)))
                assertTrue(it.window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE != 0)
            }
            val notice = app.getString(R.string.private_download_notice)
            eventually { InstrumentationRegistry.getInstrumentation().uiAutomation.rootInActiveWindow
                ?.findAccessibilityNodeInfosByText(notice)?.any { it.isVisibleToUser } == true }
            assertFalse(body.closed.get())
            scenario.recreate()
            assertEquals(DownloadController.Status.OFFERED, fromMain { app.downloads.offer!!.status })
            scenario.onActivity { app.browser.closePrivateTabs() }
            assertTrue(body.closed.get())
            assertTrue(fromMain { app.downloads.visible(BrowsingMode.PRIVATE).isEmpty() })
        }
    }
}
