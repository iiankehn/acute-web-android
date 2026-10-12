/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

import java.util.UUID
import kotlinx.serialization.Serializable

enum class BrowsingMode { NORMAL, PRIVATE }
data class BrowserTab(val id: String, val mode: BrowsingMode, val page: PageState = PageState(), val engineState: String? = null)
/** Only normal data can enter the durable session format. */
@Serializable
data class SavedTab(val id: String, val uri: String, val title: String, val engineState: String?)
@Serializable
data class SavedTabs(val selectedId: String?, val tabs: List<SavedTab>)

/** App-owned selection policy. Engine state is Gecko's opaque snapshot, never a second history implementation. */
class Tabs {
    companion object { const val MAX_NORMAL = 32; const val MAX_PRIVATE = 16; const val MAX_ENGINE_STATE = 262144 }
    private val entries = linkedMapOf<String, BrowserTab>()
    private val selections = mutableMapOf<BrowsingMode, String>()
    var mode = BrowsingMode.NORMAL
        private set
    val all: List<BrowserTab> get() = entries.values.toList()
    val visible: List<BrowserTab> get() = all.filter { it.mode == mode }
    val selected: BrowserTab? get() = selections[mode]?.let(entries::get)

    fun add(target: BrowsingMode = mode): BrowserTab? {
        val limit = if (target == BrowsingMode.NORMAL) MAX_NORMAL else MAX_PRIVATE
        if (entries.values.count { it.mode == target } >= limit) return null
        val tab = BrowserTab(UUID.randomUUID().toString(), target)
        entries[tab.id] = tab; selections[target] = tab.id; mode = target
        return tab
    }
    fun switchMode(target: BrowsingMode) { mode = target }
    fun select(id: String) { val tab = entries[id] ?: return; mode = tab.mode; selections[mode] = id }
    fun get(id: String) = entries[id]
    fun update(id: String, page: PageState) {
        val old = entries[id] ?: return
        // Never pair a newly navigated URL with stale state for the old document.
        entries[id] = old.copy(page = page, engineState = if (old.page.uri == page.uri) old.engineState else null)
    }
    fun saveEngineState(id: String, state: String?) {
        val old = entries[id] ?: return
        entries[id] = old.copy(engineState = state?.takeIf { it.length <= MAX_ENGINE_STATE })
    }
    fun close(id: String): BrowserTab? {
        val old = entries.remove(id) ?: return null
        if (selections[old.mode] == id) {
            selections.remove(old.mode)
            entries.values.lastOrNull { it.mode == old.mode }?.let { selections[old.mode] = it.id }
        }
        return old
    }
    fun normalSnapshot(): SavedTabs = SavedTabs(selections[BrowsingMode.NORMAL], all.filter { it.mode == BrowsingMode.NORMAL }.map {
        SavedTab(it.id, it.page.uri.takeIf { uri -> uri.isEmpty() || (uri.length <= 4096 && NavigationPolicy.allows(uri)) }.orEmpty(), it.page.title.take(512), it.engineState)
    })
    fun restore(saved: SavedTabs) {
        require(saved.tabs.size <= MAX_NORMAL)
        require(saved.tabs.map { it.id }.distinct().size == saved.tabs.size)
        require(saved.tabs.all { it.id.matches(Regex("[a-zA-Z0-9-]{1,64}")) &&
            (it.uri.isEmpty() || (it.uri.length <= 4096 && NavigationPolicy.allows(it.uri))) &&
            it.title.length <= 512 && (it.engineState?.length ?: 0) <= MAX_ENGINE_STATE })
        entries.clear(); selections.clear(); mode = BrowsingMode.NORMAL
        saved.tabs.forEach { entries[it.id] = BrowserTab(it.id, BrowsingMode.NORMAL, PageState(uri = it.uri, title = it.title), it.engineState) }
        val selected = saved.selectedId?.takeIf { entries.containsKey(it) } ?: entries.keys.firstOrNull()
        if (selected != null) selections[BrowsingMode.NORMAL] = selected
    }
}
