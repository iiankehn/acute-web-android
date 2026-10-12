package com.acuteweb.nativeapp

import android.view.WindowManager
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.acuteweb.core.*
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.mozilla.geckoview.GeckoSession
import org.json.JSONObject
import java.net.*
import java.io.File
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

internal fun onMain(block: () -> Unit) = InstrumentationRegistry.getInstrumentation().runOnMainSync(block)
internal fun <T> fromMain(block: () -> T): T {
    val result = AtomicReference<T>()
    onMain { result.set(block()) }
    return result.get()
}
internal fun eventually(condition: () -> Boolean) {
    val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(20)
    while (System.nanoTime() < deadline) { if (condition()) return; Thread.sleep(50) }
    assertTrue("Timed out waiting for browser state", condition())
}
internal val app get() = InstrumentationRegistry.getInstrumentation().targetContext.applicationContext as AcuteApplication

/** Offline HTTP fixture. No public network, mocked Gecko, or certificate bypass. */
internal class TestSite(port: Int = 0) : AutoCloseable {
    private val server = ServerSocket(port, 50, InetAddress.getByName("127.0.0.1"))
    private val running = AtomicBoolean(true)
    val port get() = server.localPort
    private val worker = Thread {
        while (running.get()) {
            try {
                server.accept().use { client ->
                    client.soTimeout = 5000
                    val reader = client.getInputStream().bufferedReader()
                    val line = reader.readLine() ?: return@use
                    val path = line.split(' ').getOrNull(1) ?: "/"
                    while (!reader.readLine().isNullOrEmpty()) { }
                    val token = path.substringAfter("token=", "fixture")
                    val marker = when { path.startsWith("/normal-set") -> "normal"; path.startsWith("/private-set") -> "private"; else -> null }
                    val body = "<html><head><script>document.title=" + JSONObject.quote(token + ":") + "+document.cookie;</script></head><body>Offline fixture</body></html>"
                    val bytes = body.toByteArray(Charsets.UTF_8)
                    val cookie = if (marker != null) "Set-Cookie: marker=$marker; Path=/; SameSite=Lax\r\n" else ""
                    val headers = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n${cookie}Content-Length: ${bytes.size}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n"
                    client.getOutputStream().write(headers.toByteArray(Charsets.US_ASCII)); client.getOutputStream().write(bytes)
                }
            } catch (_: Exception) { if (!running.get()) break }
        }
    }.apply { isDaemon = true; start() }
    fun uri(path: String, token: String = UUID.randomUUID().toString()) = URI("http", null, "127.0.0.1", port, path, "token=$token", null).toASCIIString()
    override fun close() { running.set(false); server.close(); worker.join(1000) }
}
internal class SessionDriver(private: Boolean = false, context: String? = null, initial: PageState = PageState(), history: PlacesStore? = null) : AutoCloseable {
    lateinit var engine: GeckoBrowserEngine
    val page = AtomicReference(initial)
    val snapshot = AtomicReference<String?>(null)
    init { onMain { engine = GeckoBrowserEngine(app.runtime, private, context, initial, { page.set(it) }, { snapshot.set(it) }, { null }, { }, history) } }
    fun open(state: String? = null) { onMain { engine.open(state); engine.visibility(true) } }
    fun load(uri: String, token: String): String {
        onMain { engine.navigate(uri) }
        eventually { page.get().title.startsWith(token + ":") }
        return page.get().title.substringAfter(':')
    }
    override fun close() { onMain { engine.close() } }
}
@RunWith(AndroidJUnit4::class)
class BrowserDeviceTest {
    @Test fun androidKeystoreAndAtomicFilePreserveEncryptedSnapshots() {
        val name = "archive-test-${UUID.randomUUID()}.enc"
        val store = SessionArchive(app, name)
        val saved = SavedTabs("one", listOf(SavedTab("one", "https://example.com/normal", "Normal", "opaque-state")))
        store.write(saved); assertEquals(saved, store.read())
        val file = File(app.noBackupFilesDir, name)
        val bytes = file.readBytes()
        assertFalse(bytes.toString(Charsets.ISO_8859_1).contains("opaque-state"))
        bytes[bytes.lastIndex] = (bytes.last().toInt() xor 1).toByte(); file.writeBytes(bytes)
        try { store.read(); fail("Tampered archive accepted") } catch (_: Exception) { }
        file.delete()
    }
    @Test fun unreadableArchiveCannotBeOverwrittenByNewBrowsing() {
        val name = "failed-read-${UUID.randomUUID()}.enc"
        val archive = SessionArchive(app, name)
        archive.write(SavedTabs("previous", listOf(SavedTab("previous", "https://example.com/preserved", "Preserved", null))))
        val file = File(app.noBackupFilesDir, name)
        val damaged = file.readBytes().apply { this[lastIndex] = (this[lastIndex].toInt() xor 1).toByte() }
        file.writeBytes(damaged)
        lateinit var browser: BrowserController
        onMain { browser = BrowserController(app, app.runtime, archive) }
        eventually { fromMain { browser.ready } }
        assertNotNull(fromMain { browser.storageError })
        onMain { browser.newTab(); browser.persistNow() }
        assertArrayEquals(damaged, file.readBytes())
        file.delete()
    }
    @Test fun privateCookiesArePartitionedAndNewPrivateWindowsStartEmpty() {
        TestSite().use { site ->
            val context = UUID.randomUUID().toString()
            SessionDriver().use { normal ->
                normal.open()
                val n1 = UUID.randomUUID().toString()
                assertEquals("marker=normal", normal.load(site.uri("/normal-set", n1), n1))
                SessionDriver(true, context).use { private ->
                    private.open(); val p1 = UUID.randomUUID().toString()
                    assertEquals("", private.load(site.uri("/read", p1), p1))
                    val p2 = UUID.randomUUID().toString()
                    assertEquals("marker=private", private.load(site.uri("/private-set", p2), p2))
                    val n2 = UUID.randomUUID().toString()
                    assertEquals("marker=normal", normal.load(site.uri("/read", n2), n2))
                    SessionDriver(true, context).use { sameWindow ->
                        sameWindow.open(); val p3 = UUID.randomUUID().toString()
                        assertEquals("marker=private", sameWindow.load(site.uri("/read", p3), p3))
                    }
                }
                onMain { app.runtime.storageController.clearDataForSessionContext(context) }
                SessionDriver(true, UUID.randomUUID().toString()).use { fresh ->
                    fresh.open(); val p4 = UUID.randomUUID().toString()
                    assertEquals("", fresh.load(site.uri("/read", p4), p4))
                }
            }
        }
    }
    @Test fun geckoHistoryRestoresFromAnEncryptedArchive() {
        TestSite().use { site ->
            val first = UUID.randomUUID().toString(); val second = UUID.randomUUID().toString()
            val firstUri = site.uri("/first", first); val secondUri = site.uri("/second", second)
            lateinit var saved: SavedTabs
            SessionDriver().use { original ->
                original.open(); original.load(firstUri, first); original.load(secondUri, second)
                onMain { original.engine.flush() }
                eventually { original.snapshot.get()?.contains(second) == true && original.page.get().canGoBack }
                saved = SavedTabs("restored", listOf(SavedTab("restored", secondUri, second + ":", original.snapshot.get())))
            }
            val name = "restore-test-${UUID.randomUUID()}.enc"; val archive = SessionArchive(app, name)
            archive.write(saved); val restored = archive.read().tabs.single()
            SessionDriver(initial = PageState(uri = restored.uri)).use { session ->
                session.open(restored.engineState)
                eventually { session.page.get().title.startsWith(second + ":") && session.page.get().canGoBack }
                onMain { session.engine.back() }
                eventually { session.page.get().title.startsWith(first + ":") }
            }
            File(app.noBackupFilesDir, name).delete()
        }
    }
    @Test fun rotationKeepsPrivateSessionAndScreenshotProtection() {
        ActivityScenario.launch(BrowserActivity::class.java).use { scenario ->
            lateinit var selected: GeckoSession
            eventually { fromMain { app.browser.ready } }
            scenario.onActivity {
                app.browser.newTab(BrowsingMode.PRIVATE)
                selected = app.browser.selectedEngine()!!.session
                assertTrue(selected.settings.usePrivateMode)
                assertTrue(it.window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE != 0)
            }
            scenario.recreate()
            scenario.onActivity {
                assertEquals(BrowsingMode.PRIVATE, app.browser.tabs.mode)
                assertSame(selected, app.browser.selectedEngine()!!.session)
                assertTrue(it.window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE != 0)
                app.browser.closePrivateTabs()
                assertEquals(0, app.browser.tabs.all.count { tab -> tab.mode == BrowsingMode.PRIVATE })
            }
            eventually { var safe = false; scenario.onActivity { safe = it.window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE == 0 }; safe }
        }
    }
}
