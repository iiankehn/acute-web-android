/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfDocument
import android.graphics.pdf.PdfRenderer
import android.os.*
import android.print.PrintManager
import android.view.KeyEvent
import android.view.WindowManager
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.acuteweb.core.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.*
import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

private fun fixturePdf(): ByteArray {
    val document = PdfDocument()
    try {
    val page = document.startPage(PdfDocument.PageInfo.Builder(200, 300, 1).create())
    page.canvas.drawColor(Color.BLUE); document.finishPage(page)
    return ByteArrayOutputStream().also { document.writeTo(it) }.toByteArray()
    } finally { document.close() }
}
private fun tracked(bytes: ByteArray, closed: AtomicBoolean) = object : ByteArrayInputStream(bytes) {
    override fun close() { closed.set(true); super.close() }
}
@RunWith(AndroidJUnit4::class)
class DocumentDeviceTest {
    @Test fun unrequestedWebsitePrintStreamsAreClosedWithoutExporting() {
        val closed = AtomicBoolean()
        SessionDriver(private = true, context = UUID.randomUUID().toString()).use { browser ->
            onMain {
                val delegate = browser.engine.session.printDelegate!!
                assertNotNull(delegate.onPrintWithStatus(tracked(fixturePdf(), closed)))
            }
            assertTrue(closed.get())
        }
    }
    @Test fun geckoExportsAllPagesIncludingContentBelowTheViewport() {
        val file = File(app.cacheDir, "export-test-${UUID.randomUUID()}.pdf")
        try {
            TestSite().use { site -> SessionDriver().use { browser ->
                browser.open(); val token = UUID.randomUUID().toString()
                browser.load(site.uri("/long-document", token), token)
                val response = AtomicReference<Result<InputStream>?>(null)
                onMain { browser.engine.pdf { response.set(it) } }
                eventually { response.get() != null }
                val stream = response.get()!!.getOrThrow()
                DownloadPolicy.copy(stream, FileOutputStream(file))
                assertTrue(file.length() > 1000)
                PdfRenderer(ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)).use { renderer ->
                    assertEquals(3, renderer.pageCount)
                    renderer.openPage(2).use { last ->
                        val bitmap = Bitmap.createBitmap(last.width, last.height, Bitmap.Config.ARGB_8888)
                        bitmap.eraseColor(Color.WHITE); last.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                        val pixels = IntArray(bitmap.width * bitmap.height)
                        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
                        assertTrue("Last-page green marker missing", pixels.any { Color.green(it) > 200 && Color.red(it) < 60 && Color.blue(it) < 60 })
                        bitmap.recycle()
                    }
                }
            } }
        } finally { file.delete() }
    }
    @Test fun printCopyIsExactCancelledWritesFailAndTemporaryFilesAreRemoved() {
        val bytes = fixturePdf(); val sourceClosed = AtomicBoolean()
        val adapter = PdfPrintAdapter.prepare(app, tracked(bytes, sourceClosed), "fixture.pdf") { false }
        val destination = File(app.cacheDir, "print-output-${UUID.randomUUID()}.pdf")
        try {
            assertTrue(sourceClosed.get()); assertEquals(1, adapter.pageCount)
            val result = AtomicReference<Result<Long>?>(null)
            onMain { adapter.write(ParcelFileDescriptor.open(destination, ParcelFileDescriptor.MODE_CREATE or ParcelFileDescriptor.MODE_TRUNCATE or ParcelFileDescriptor.MODE_WRITE_ONLY), CancellationSignal()) { result.set(it) } }
            eventually { result.get() != null }
            assertEquals(bytes.size.toLong(), result.get()!!.getOrThrow()); assertArrayEquals(bytes, destination.readBytes())
            result.set(null)
            val signal = CancellationSignal().apply { cancel() }
            onMain { adapter.write(ParcelFileDescriptor.open(destination, ParcelFileDescriptor.MODE_WRITE_ONLY), signal) { result.set(it) } }
            eventually { result.get() != null }; assertTrue(result.get()!!.isFailure)
        } finally { onMain { adapter.onFinish() }; destination.delete() }
        eventually { !adapter.file.exists() }
    }
    @Test fun invalidOrCancelledGenerationClosesItsStreamAndKeepsOtherCacheFiles() {
        val unrelated = File(app.cacheDir, "unrelated-${UUID.randomUUID()}.pdf").apply { writeBytes(byteArrayOf(8, 9)) }
        try {
            val closed = AtomicBoolean()
            try { PdfPrintAdapter.prepare(app, tracked(byteArrayOf(1, 2), closed), "bad.pdf") { false }; fail("Invalid PDF accepted") } catch (_: Exception) { }
            assertTrue(closed.get())
            closed.set(false)
            try { PdfPrintAdapter.prepare(app, tracked(fixturePdf(), closed), "cancelled.pdf") { true }; fail("Cancelled generation accepted") } catch (_: InterruptedIOException) { }
            assertTrue(closed.get())
            PdfPrintAdapter.clearAbandoned(app)
            assertArrayEquals(byteArrayOf(8, 9), unrelated.readBytes())
        } finally { unrelated.delete() }
    }
    @Test fun privatePrintingRequiresExplicitProtectedConsentBeforeCreatingACacheFile() {
        TestSite().use { site ->
        ActivityScenario.launch(BrowserActivity::class.java).use { scenario ->
            eventually { fromMain { app.browser.ready } }
            lateinit var ui: DocumentUi
            scenario.onActivity { activity ->
                app.browser.newTab(BrowsingMode.PRIVATE); app.browser.navigate(site.uri("/private-print"))
                ui = DocumentUi(activity, app.browser, app.downloads)
                assertTrue(ui.printAvailable); ui.export(true)
                assertTrue(activity.window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE != 0)
            }
            val notice = app.getString(R.string.private_print_notice)
            eventually { InstrumentationRegistry.getInstrumentation().uiAutomation.rootInActiveWindow
                ?.findAccessibilityNodeInfosByText(notice)?.any { it.isVisibleToUser } == true }
            assertTrue(File(app.cacheDir, "acute-print").listFiles().orEmpty().isEmpty())
            scenario.onActivity { ui.destroy(); app.browser.closePrivateTabs() }
        }
        }
    }
    @Test fun androidPrintServiceOpensAndCancelRemovesTheOwnedTemporaryDocument() {
        val adapter = PdfPrintAdapter.prepare(app, ByteArrayInputStream(fixturePdf()), "acute-print-fixture.pdf") { false }
        try {
            ActivityScenario.launch(BrowserActivity::class.java).use { scenario ->
                eventually { fromMain { app.browser.ready } }
                scenario.onActivity { it.getSystemService(PrintManager::class.java).print("Acute fixture", adapter, null) }
                val automation = InstrumentationRegistry.getInstrumentation().uiAutomation
                eventually { automation.rootInActiveWindow?.packageName?.toString() == "com.android.printspooler" }
                // Back can dismiss the keyboard or an expanded print option before the print Activity.
                // Wait for each UI transition and leave the actual spooler; do not call onFinish ourselves.
                repeat(4) {
                    if (automation.rootInActiveWindow?.packageName?.toString() == "com.android.printspooler") {
                        automation.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK)
                        automation.waitForIdle(500, 5000)
                    }
                }
                eventually { adapter.closed && !adapter.file.exists() }
            }
        } finally { onMain { adapter.onFinish() } }
    }
}
