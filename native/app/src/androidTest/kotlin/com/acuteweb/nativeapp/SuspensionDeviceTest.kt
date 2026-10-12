/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.acuteweb.core.BrowsingMode
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.mozilla.geckoview.GeckoSession
import java.util.UUID
import java.util.concurrent.atomic.AtomicReference

@RunWith(AndroidJUnit4::class)
class SuspensionDeviceTest {
    @Test fun suspendingBackgroundTabClosesGeckoAndSelectionRestoresItsHistory() {
        TestSite().use { site ->
            ActivityScenario.launch(BrowserActivity::class.java).use {
                eventually { fromMain { app.browser.ready } }
                val first = UUID.randomUUID().toString(); val second = UUID.randomUUID().toString()
                lateinit var id: String
                lateinit var original: GeckoSession
                onMain {
                    app.browser.newTab(BrowsingMode.NORMAL); id = app.browser.tabs.selected!!.id
                    original = app.browser.selectedEngine()!!.session
                    app.browser.navigate(site.uri("/suspend-first", first))
                }
                eventually { fromMain { app.browser.tabs.get(id)?.page?.title?.startsWith(first + ":") == true } }
                onMain { app.browser.navigate(site.uri("/suspend-second", second)) }
                eventually { fromMain { app.browser.tabs.get(id)?.page?.title?.startsWith(second + ":") == true && app.browser.tabs.get(id)?.page?.canGoBack == true } }
                onMain {
                    assertFalse(app.browser.suspendTab(id)) // Active pages are never closed.
                    app.browser.newTab(BrowsingMode.NORMAL)
                    assertTrue(app.browser.suspendTab(id))
                }
                eventually { fromMain { app.browser.isSuspended(id) } }
                assertFalse(fromMain { original.isOpen })
                eventually { runCatching { SessionArchive(app).read().tabs.any { tab -> tab.id == id && tab.engineState?.contains(second) == true } }.getOrDefault(false) }
                onMain { app.browser.select(id); assertNotSame(original, app.browser.selectedEngine()!!.session) }
                eventually { fromMain { app.browser.tabs.selected?.page?.title?.startsWith(second + ":") == true && app.browser.tabs.selected?.page?.canGoBack == true && app.browser.tabs.selected?.page?.loading == false } }
                onMain { app.browser.selectedEngine()!!.back() }
                eventually { fromMain { app.browser.tabs.selected?.page?.title?.startsWith(first + ":") == true } }
            }
        }
    }
    @Test fun selectingAPendingTabCancelsSuspensionAndKeepsTheSameSession() {
        TestSite().use { site ->
            ActivityScenario.launch(BrowserActivity::class.java).use {
                eventually { fromMain { app.browser.ready } }
                val token = UUID.randomUUID().toString()
                lateinit var id: String
                lateinit var original: GeckoSession
                val result = AtomicReference<Boolean?>(null)
                onMain {
                    app.browser.newTab(BrowsingMode.NORMAL); id = app.browser.tabs.selected!!.id
                    original = app.browser.selectedEngine()!!.session
                    app.browser.navigate(site.uri("/cancel-suspend", token))
                }
                eventually { fromMain { app.browser.tabs.get(id)?.page?.title?.startsWith(token + ":") == true } }
                onMain {
                    app.browser.newTab(BrowsingMode.NORMAL)
                    assertTrue(app.browser.suspendTab(id) { result.set(it) })
                    app.browser.select(id)
                    assertSame(original, app.browser.selectedEngine()!!.session)
                    assertTrue(original.isOpen); assertFalse(app.browser.isSuspended(id))
                }
                assertEquals(false, result.get())
            }
        }
    }
    @Test fun privateTabsAreNeverSuspendedOrAddedToTheNormalArchive() {
        ActivityScenario.launch(BrowserActivity::class.java).use {
            eventually { fromMain { app.browser.ready } }
            onMain {
                app.browser.newTab(BrowsingMode.PRIVATE)
                val privateId = app.browser.tabs.selected!!.id
                val privateSession = app.browser.selectedEngine()!!.session
                app.browser.newTab(BrowsingMode.NORMAL)
                assertFalse(app.browser.canSuspend(privateId)); assertFalse(app.browser.suspendTab(privateId))
                assertFalse(app.browser.isSuspended(privateId)); assertTrue(privateSession.isOpen)
                assertFalse(app.browser.tabs.normalSnapshot().tabs.any { tab -> tab.id == privateId })
                app.browser.closePrivateTabs()
            }
        }
    }
}
