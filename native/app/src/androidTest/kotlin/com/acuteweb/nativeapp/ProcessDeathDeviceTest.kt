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
    private val libraryName = "process-death-places.sqlite"
    @Test fun prepare() {
        TestSite(38263).use { site ->
            val archive = SessionArchive(app, archiveName)
            val places = PlacesStore(app, libraryName)
            lateinit var browser: BrowserController
            onMain { browser = BrowserController(app, app.runtime, archive, places) }
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
            storage<String> { places.saveBookmark(BrowsingMode.NORMAL, normal, "Process bookmark", it) }
            // Keep the process-owned store live until the external force-stop.
            val saved = archive.read()
            assertFalse(saved.toString().contains("private-secret"))
            assertFalse(saved.toString().contains("process-private"))
        }
    }
    @Test fun verify() {
        TestSite(38263).use {
            val places = PlacesStore(app, libraryName)
            lateinit var browser: BrowserController
            onMain { browser = BrowserController(app, app.runtime, SessionArchive(app, archiveName), places) }
            eventually { fromMain { browser.ready } }
            assertNull(browser.storageError)
            assertEquals(BrowsingMode.NORMAL, browser.tabs.mode)
            assertTrue(browser.tabs.all.isNotEmpty())
            assertTrue(browser.tabs.all.all { tab -> tab.mode == BrowsingMode.NORMAL })
            assertTrue(browser.tabs.selected!!.page.uri.contains("/restore-me"))
            assertTrue(browser.tabs.selected!!.engineState!!.contains("process-normal"))
            assertFalse(browser.tabs.all.toString().contains("process-private"))
            assertTrue(storage<List<PlacesStore.Bookmark>> { places.bookmarks(it) }.any { bookmark -> bookmark.title == "Process bookmark" })
            val visits = storage<List<PlacesStore.Visit>> { places.history(it) }
            assertTrue(visits.any { visit -> visit.uri.contains("restore-me") })
            assertFalse(visits.any { visit -> visit.uri.contains("private-secret") })
            storage<Unit> { places.close(it) }
        }
    }
}
