/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import androidx.test.ext.junit.runners.AndroidJUnit4
import com.acuteweb.core.PageState
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.mozilla.geckoview.GeckoSession
import org.mozilla.geckoview.WebResponse
import java.io.ByteArrayInputStream
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

@RunWith(AndroidJUnit4::class)
class AdapterDeviceTest {
    @Test fun ignoredExternalResponseAlwaysClosesItsStream() {
        val closed = AtomicBoolean(false)
        val body = object : ByteArrayInputStream(byteArrayOf(1, 2, 3)) {
            override fun close() { closed.set(true); super.close() }
        }
        SessionDriver().use { driver ->
            onMain {
                val response = WebResponse.Builder("https://example.com/download").statusCode(200).body(body).build()
                driver.engine.session.contentDelegate!!.onExternalResponse(driver.engine.session, response)
            }
            assertTrue(closed.get())
            assertNotNull(driver.page.get().error)
        }
    }
    @Test fun contextBoundaryRejectsPrivilegedSchemesAndAcceptsWebLinks() {
        val link = AtomicReference<String?>(null)
        lateinit var engine: GeckoBrowserEngine
        onMain {
            engine = GeckoBrowserEngine(app.runtime, false, null, PageState(), {}, {}, { null }, {}, linkContext = { link.set(it) })
            fun element(uri: String) = object : GeckoSession.ContentDelegate.ContextElement(null, uri, null, null, "", null, null) {}
            engine.session.contentDelegate!!.onContextMenu(engine.session, 0, 0, element("javascript:alert(1)"))
            assertNull(link.get())
            engine.session.contentDelegate!!.onContextMenu(engine.session, 0, 0, element("https://example.com/?utm_source=ad"))
            assertEquals("https://example.com/?utm_source=ad", link.get())
            engine.close()
        }
    }
}
