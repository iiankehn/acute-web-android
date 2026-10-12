/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.acuteweb.core.*
import org.mozilla.geckoview.GeckoRuntime
import org.mozilla.geckoview.GeckoSession
import java.util.UUID
import java.util.concurrent.Executors

/** Process-owned sessions survive Activity recreation. No Activity/View reference is retained after detach. */
class BrowserController(context: Context, private val runtime: GeckoRuntime, private val archive: SessionArchive = SessionArchive(context.applicationContext), private val places: PlacesStore? = (context.applicationContext as? AcuteApplication)?.places, private val downloads: DownloadController? = (context.applicationContext as? AcuteApplication)?.downloads) {
    var linkHandler: ((String, String) -> Unit)? = null
    val tabs = Tabs()
    var ready = false
        private set
    var storageError: String? = null
        private set
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private val listeners = linkedSetOf<() -> Unit>()
    private val engines = linkedMapOf<String, GeckoBrowserEngine>()
    private var privateContext = UUID.randomUUID().toString()
    private var canPersist = true
    private var resetting = false
    /** True while an unreadable saved-tabs archive is being preserved untouched; see [resetSavedTabs]. */
    val needsRecovery: Boolean get() = !canPersist
    private val persistTask = Runnable { persistNow() }

    init {
        io.execute {
            val result = runCatching { archive.read() }
            main.post {
                result.onSuccess { tabs.restore(it) }.onFailure {
                    canPersist = false
                    storageError = "Saved tabs could not be restored. The original data is kept until you reset it from the menu."
                }
                if (tabs.selected == null) tabs.add(BrowsingMode.NORMAL)
                ready = true; emit()
            }
        }
    }
    private fun checkThread() { check(Looper.myLooper() == Looper.getMainLooper()) }
    fun attach(listener: () -> Unit) { checkThread(); listeners.add(listener); emit() }
    fun detach(listener: () -> Unit) {
        checkThread(); listeners.remove(listener)
        if (listeners.isEmpty()) { engines.values.forEach { it.visibility(false); it.flush() }; persistNow() }
    }
    fun selectedEngine(): GeckoBrowserEngine? {
        checkThread(); val tab = tabs.selected ?: return null
        if (!ready) return null
        return engines[tab.id] ?: createEngine(tab).also { it.open(tab.engineState) }
    }
    private fun createEngine(tab: BrowserTab): GeckoBrowserEngine {
        val engine = GeckoBrowserEngine(runtime, tab.mode == BrowsingMode.PRIVATE, privateContext, tab.page,
            changed = { page ->
                tabs.update(tab.id, page)
                if (tab.mode == BrowsingMode.NORMAL) scheduleSave()
                emit()
            },
            snapshot = { state ->
                tabs.saveEngineState(tab.id, state)
                if (tab.mode == BrowsingMode.NORMAL) scheduleSave()
            },
            newWindow = { uri ->
                // Gecko requires an unopened session. Attach the view only after Gecko opens it.
                if (tabs.selected?.id != tab.id || !NavigationPolicy.allowsOrBlank(uri)) null
                else tabs.add(tab.mode)?.let { created ->
                    val child = createEngine(created)
                    main.post { emit(); if (created.mode == BrowsingMode.NORMAL) scheduleSave() }
                    child.session
                }
            },
            closeWindow = { close(tab.id) },
            history = places,
            downloadResponse = downloads?.let { manager -> { mode, response -> manager.receive(mode, response) } },
            linkContext = { uri -> if (tabs.selected?.id == tab.id) linkHandler?.invoke(tab.id, uri) },
        )
        engines[tab.id] = engine
        return engine
    }
    private fun emit() {
        if (ready && listeners.isNotEmpty()) selectedEngine()
        val selected = tabs.selected?.id
        engines.forEach { (id, engine) -> engine.visibility(listeners.isNotEmpty() && id == selected) }
        listeners.toList().forEach { it() }
    }
    fun newTab(mode: BrowsingMode = tabs.mode): Boolean {
        checkThread(); if (!ready) return false
        if (tabs.add(mode) == null) return false
        emit(); if (mode == BrowsingMode.NORMAL) persistNow(); return true
    }
    fun select(id: String) {
        checkThread(); if (!ready) return
        tabs.select(id); emit()
        if (tabs.mode == BrowsingMode.NORMAL) persistNow()
    }
    fun switchMode(mode: BrowsingMode) {
        checkThread(); if (!ready) return
        tabs.switchMode(mode)
        if (tabs.selected == null) tabs.add(mode)
        emit()
    }
    fun close(id: String) {
        checkThread(); val removed = tabs.close(id) ?: return
        engines.remove(id)?.close()
        if (removed.mode == BrowsingMode.PRIVATE && tabs.all.none { it.mode == BrowsingMode.PRIVATE }) {
            runtime.storageController.clearDataForSessionContext(privateContext)
            privateContext = UUID.randomUUID().toString()
            downloads?.forgetPrivate()
            tabs.switchMode(BrowsingMode.NORMAL)
        }
        if (tabs.selected == null) tabs.add(tabs.mode)
        emit(); if (removed.mode == BrowsingMode.NORMAL) persistNow()
    }
    fun closePrivateTabs() {
        checkThread(); downloads?.forgetPrivate(); val ids = tabs.all.filter { it.mode == BrowsingMode.PRIVATE }.map { it.id }
        ids.forEach { engines.remove(it)?.close(); tabs.close(it) }
        if (ids.isNotEmpty()) {
            runtime.storageController.clearDataForSessionContext(privateContext)
            privateContext = UUID.randomUUID().toString()
        }
        tabs.switchMode(BrowsingMode.NORMAL)
        if (ready && tabs.selected == null) tabs.add(BrowsingMode.NORMAL)
        emit()
    }
    fun navigate(input: String): Boolean {
        checkThread(); if (!ready) return false
        val uri = NavigationPolicy.address(input)?.takeIf { it.length <= 4096 } ?: return false
        selectedEngine()?.navigate(uri); return true
    }
    private fun scheduleSave() {
        if (!ready || !canPersist) return
        main.removeCallbacks(persistTask); main.postDelayed(persistTask, 400)
    }
    /** Replace only after confirmation; AtomicFile keeps the unreadable archive if the new write fails. */
    fun resetSavedTabs() {
        checkThread(); if (!ready || canPersist || resetting) return
        resetting = true
        val saved = tabs.normalSnapshot()
        io.execute {
            val result = runCatching { archive.write(saved) }
            main.post {
                resetting = false
                if (result.isSuccess) {
                    canPersist = true; storageError = null
                    // Capture any browsing changes made while the replacement was being written.
                    persistNow()
                } else storageError = "Saved tabs could not be reset. The original data has been kept."
                listeners.toList().forEach { it() }
            }
        }
    }
    fun persistNow() {
        checkThread(); main.removeCallbacks(persistTask)
        if (!ready || !canPersist) return
        val saved = tabs.normalSnapshot()
        io.execute {
            val result = runCatching { archive.write(saved) }
            main.post {
                storageError = if (result.isFailure) "Tabs could not be saved. Your last saved session has been kept." else null
                // Persistence status only: avoid flushing/recreating sessions here.
                listeners.toList().forEach { it() }
            }
        }
    }
}
