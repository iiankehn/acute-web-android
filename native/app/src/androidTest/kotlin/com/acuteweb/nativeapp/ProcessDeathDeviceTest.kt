package com.acuteweb.nativeapp

import androidx.test.ext.junit.runners.AndroidJUnit4
import com.acuteweb.core.BrowsingMode
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Run the two methods in separate instrumentation invocations, with am force-stop between them. */
@RunWith(AndroidJUnit4::class)
class ProcessDeathDeviceTest {
    private val archiveName = "process-death-fixture.enc"
    @Test fun prepare() {
        TestSite(38263).use { site ->
            val archive = SessionArchive(app, archiveName)
            lateinit var browser: BrowserController
            onMain { browser = BrowserController(app, app.runtime, archive) }
            eventually { fromMain { browser.ready } }
            val normal = site.uri("/restore-me", "process-normal")
            val private = site.uri("/private-secret", "process-private")
            onMain { browser.attach { }; browser.navigate(normal) }
            eventually { fromMain { browser.tabs.selected?.page?.title?.startsWith("process-normal:") == true } }
            onMain { browser.selectedEngine()!!.flush() }
            eventually { fromMain { browser.tabs.selected?.engineState?.contains("process-normal") == true } }
            onMain { browser.newTab(BrowsingMode.PRIVATE); browser.navigate(private) }
            eventually { fromMain { browser.tabs.selected?.page?.title?.startsWith("process-private:") == true } }
            onMain { browser.persistNow() }
            eventually { runCatching { archive.read().tabs.any { it.uri == normal } }.getOrDefault(false) }
            val saved = archive.read()
            assertFalse(saved.toString().contains("private-secret"))
            assertFalse(saved.toString().contains("process-private"))
        }
    }
    @Test fun verify() {
        TestSite(38263).use {
            lateinit var browser: BrowserController
            onMain { browser = BrowserController(app, app.runtime, SessionArchive(app, archiveName)) }
            eventually { fromMain { browser.ready } }
            assertNull(browser.storageError)
            assertEquals(BrowsingMode.NORMAL, browser.tabs.mode)
            assertTrue(browser.tabs.all.isNotEmpty())
            assertTrue(browser.tabs.all.all { tab -> tab.mode == BrowsingMode.NORMAL })
            assertTrue(browser.tabs.selected!!.page.uri.contains("/restore-me"))
            assertTrue(browser.tabs.selected!!.engineState!!.contains("process-normal"))
            assertFalse(browser.tabs.all.toString().contains("process-private"))
        }
    }
}
