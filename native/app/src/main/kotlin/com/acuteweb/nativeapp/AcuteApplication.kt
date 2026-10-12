/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.app.Application
import org.mozilla.geckoview.ContentBlocking
import org.mozilla.geckoview.GeckoRuntime
import org.mozilla.geckoview.GeckoRuntimeSettings

class AcuteApplication : Application() {
    override fun onCreate() { super.onCreate(); PdfPrintAdapter.clearAbandoned(this) }
    val downloads: DownloadController by lazy { DownloadController(this) }
    val places: PlacesStore by lazy { PlacesStore(this) }
    val extensions: ExtensionManager by lazy { ExtensionManager(runtime) }
    val browser: BrowserController by lazy { BrowserController(this, runtime, extensions = extensions) }
    // Exactly one runtime per process; no activity context retained.
    val runtime: GeckoRuntime by lazy {
        GeckoRuntime.create(this, GeckoRuntimeSettings.Builder()
            .remoteDebuggingEnabled(false)
            .consoleOutput(false)
            .debugLogging(false)
            .aboutConfigEnabled(false)
            .contentBlocking(ContentBlocking.Settings.Builder()
                .antiTracking(ContentBlocking.AntiTracking.DEFAULT)
                .cookieBehavior(ContentBlocking.CookieBehavior.ACCEPT_NON_TRACKERS)
                .safeBrowsing(ContentBlocking.SafeBrowsing.DEFAULT)
                .build())
            .build())
    }
}
