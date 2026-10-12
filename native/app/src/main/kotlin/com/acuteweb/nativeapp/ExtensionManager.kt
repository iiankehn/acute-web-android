/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import com.acuteweb.core.*
import org.mozilla.geckoview.*
import java.util.IdentityHashMap

/** Gecko owns extension packages, signatures, updates and storage. No extension access to private tabs. */
class ExtensionManager(private val runtime: GeckoRuntime) {
    companion object {
        val BUILT_INS = linkedMapOf("acute-sessions" to "saved-sessions@acuteweb.core", "acute-notes" to "page-notes@acuteweb.core", "acute-midnight" to "midnight-pages@acuteweb.core")
    }
    private val controller get() = runtime.webExtensionController
    private var browser: BrowserController? = null
    private val installed = linkedMapOf<String, WebExtension>()
    private val defaultActions = linkedMapOf<String, WebExtension.Action>()
    private val overrides = IdentityHashMap<GeckoSession, MutableMap<String, WebExtension.Action>>()
    private val sessions = IdentityHashMap<GeckoSession, String>()
    private val listeners = linkedSetOf<() -> Unit>()
    private val pendingPrompts = linkedSetOf<(Boolean) -> Unit>()
    var popup: ((WebExtension) -> GeckoSession?)? = null
    var prompt: ((String, String, (Boolean) -> Unit) -> Unit)? = null
    var ready = false; private set
    var error: String? = null; private set
    val extensions get() = installed.values.toList()
    fun attach(listener: () -> Unit) { listeners.add(listener); listener() }
    fun detach(listener: () -> Unit) { listeners.remove(listener) }
    private fun emit() { listeners.toList().forEach { it() } }
    fun detachUi() { popup = null; prompt = null; pendingPrompts.toList().forEach { it(false) } }
    fun bind(browser: BrowserController) {
        if (this.browser != null) return
        this.browser = browser
        controller.setPromptDelegate(object : WebExtensionController.PromptDelegate {
            override fun onInstallPromptRequest(extension: WebExtension, permissions: Array<out String>, origins: Array<out String>, dataCollectionPermissions: Array<out String>): GeckoResult<WebExtension.PermissionPromptResponse> {
                val result = GeckoResult<WebExtension.PermissionPromptResponse>()
                ask(extension, permissions, origins, dataCollectionPermissions) { allowed -> result.complete(WebExtension.PermissionPromptResponse(allowed, false, false)) }
                return result
            }
            override fun onUpdatePrompt(extension: WebExtension, newPermissions: Array<out String>, newOrigins: Array<out String>, newDataCollectionPermissions: Array<out String>): GeckoResult<AllowOrDeny> {
                val result = GeckoResult<AllowOrDeny>(); ask(extension, newPermissions, newOrigins, newDataCollectionPermissions) { result.complete(if (it) AllowOrDeny.ALLOW else AllowOrDeny.DENY) }; return result
            }
            override fun onOptionalPrompt(extension: WebExtension, permissions: Array<out String>, origins: Array<out String>, dataCollectionPermissions: Array<out String>): GeckoResult<AllowOrDeny> {
                val result = GeckoResult<AllowOrDeny>(); ask(extension, permissions, origins, dataCollectionPermissions) { result.complete(if (it) AllowOrDeny.ALLOW else AllowOrDeny.DENY) }; return result
            }
        })
        var remaining = BUILT_INS.size
        fun done() { remaining--; if (remaining == 0) { ready = true; refresh() }; emit() }
        BUILT_INS.forEach { (folder, id) ->
            controller.ensureBuiltIn("resource://android/assets/extensions/$folder/", id).accept({ extension ->
                if (extension == null) { error = "Built-in extension could not be loaded"; done() }
                else controller.setAllowedInPrivateBrowsing(extension, false).accept({ updated ->
                    if (updated != null) register(updated) else error = "Private extension boundary could not be configured"
                    done()
                }, { error = "Private extension boundary could not be configured"; done() })
            }, { error = "Built-in extension could not be loaded"; done() })
        }
    }
    private fun ask(extension: WebExtension, permissions: Array<out String>, origins: Array<out String>, data: Array<out String>, reply: (Boolean) -> Unit) {
        val ui = prompt
        if (ui == null || browser?.tabs?.mode != BrowsingMode.NORMAL) { reply(false); return }
        var replied = false
        lateinit var complete: (Boolean) -> Unit
        complete = { answer -> if (!replied) { replied = true; pendingPrompts.remove(complete); reply(answer) } }
        pendingPrompts.add(complete)
        val details = (permissions.toList() + origins.toList() + data.filter { it != "none" }).joinToString("\n").take(12000)
        ui(extension.metaData?.name ?: extension.id, details, complete)
    }
    private val actions = object : WebExtension.ActionDelegate {
        override fun onBrowserAction(extension: WebExtension, session: GeckoSession?, action: WebExtension.Action) {
            if (session == null) defaultActions[extension.id] = action
            else if (session in sessions) overrides.getOrPut(session) { linkedMapOf() }[extension.id] = action
            emit()
        }
        override fun onTogglePopup(extension: WebExtension, action: WebExtension.Action): GeckoResult<GeckoSession>? = openPopup(extension)
        override fun onOpenPopup(extension: WebExtension, action: WebExtension.Action): GeckoResult<GeckoSession>? = openPopup(extension)
    }
    private fun openPopup(extension: WebExtension): GeckoResult<GeckoSession>? {
        if (browser?.tabs?.mode != BrowsingMode.NORMAL || installed[extension.id]?.metaData?.enabled != true) return null
        return popup?.invoke(extension)?.let { GeckoResult.fromValue(it) }
    }
    private fun register(extension: WebExtension) {
        installed[extension.id] = extension
        extension.setActionDelegate(actions)
        extension.setTabDelegate(object : WebExtension.TabDelegate {
            override fun onNewTab(source: WebExtension, createDetails: WebExtension.CreateTabDetails): GeckoResult<GeckoSession>? =
                browser?.extensionTab(createDetails.url, createDetails.active != false)?.let { GeckoResult.fromValue(it) }
            override fun onOpenOptionsPage(source: WebExtension) {
                if (browser?.tabs?.mode == BrowsingMode.NORMAL) popup?.invoke(source)?.let { session -> source.metaData?.optionsPageUrl?.let(session::loadUri) }
            }
        })
        sessions.forEach { (session, id) -> bindDelegates(extension, session, id) }
        emit()
    }
    private fun bindDelegates(extension: WebExtension, session: GeckoSession, id: String) {
        session.webExtensionController.setActionDelegate(extension, actions)
        session.webExtensionController.setTabDelegate(extension, object : WebExtension.SessionTabDelegate {
            override fun onCloseTab(source: WebExtension?, session: GeckoSession): GeckoResult<AllowOrDeny> {
                val b = browser ?: return GeckoResult.deny()
                if (b.tabs.mode != BrowsingMode.NORMAL || b.tabs.get(id)?.mode != BrowsingMode.NORMAL) return GeckoResult.deny()
                b.close(id); return GeckoResult.allow()
            }
            override fun onUpdateTab(extension: WebExtension, session: GeckoSession, details: WebExtension.UpdateTabDetails): GeckoResult<AllowOrDeny> {
                val b = browser ?: return GeckoResult.deny()
                if (b.tabs.mode != BrowsingMode.NORMAL || b.tabs.get(id)?.mode != BrowsingMode.NORMAL ||
                    (details.url != null && !NavigationPolicy.allows(details.url))) return GeckoResult.deny()
                if (details.active == true) b.select(id)
                return GeckoResult.allow()
            }
        })
    }
    fun bindSession(tab: BrowserTab, engine: GeckoBrowserEngine) {
        if (tab.mode != BrowsingMode.NORMAL) return
        sessions[engine.session] = tab.id
        installed.values.forEach { bindDelegates(it, engine.session, tab.id) }
    }
    fun forget(session: GeckoSession) { sessions.remove(session); overrides.remove(session) }
    fun selected(session: GeckoSession?, normal: Boolean) { sessions.keys.forEach { controller.setTabActive(it, normal && it === session) } }
    fun action(id: String): WebExtension.Action? {
        val session = browser?.selectedEngine()?.session
        val defaults = defaultActions[id]
        val specific = session?.let { overrides[it]?.get(id) }
        return if (specific != null && defaults != null) specific.withDefault(defaults) else specific ?: defaults
    }
    fun click(id: String): Boolean {
        if (browser?.tabs?.mode != BrowsingMode.NORMAL || !ready || installed[id]?.metaData?.enabled != true) return false
        val action = action(id) ?: return false
        if (action.enabled == false) return false
        action.click(); return true
    }
    fun refresh() {
        controller.list().accept({ list ->
            if (list != null) {
                val ids = list.map { it.id }.toSet()
                installed.keys.retainAll(ids); defaultActions.keys.retainAll(ids)
                list.forEach { extension ->
                    // Reapply the same private boundary on every launch, including sideloaded extensions.
                    controller.setAllowedInPrivateBrowsing(extension, false).accept({ updated -> if (updated != null) register(updated) }, { error = "Extension privacy setting failed"; emit() })
                }
            }
            emit()
        }, { error = "Extensions could not be read"; emit() })
    }
    fun install(uri: String) {
        if (browser?.tabs?.mode != BrowsingMode.NORMAL || !NavigationPolicy.allows(uri) || !uri.startsWith("https://", true)) { error = "Enter an HTTPS extension package URL"; emit(); return }
        controller.install(uri).accept({ extension -> if (extension != null) { error = null; refresh() } }, { error = "Extension could not be installed"; emit() })
    }
    fun toggle(extension: WebExtension) {
        val result = if (extension.metaData?.enabled == true) controller.disable(extension, WebExtensionController.EnableSource.USER) else controller.enable(extension, WebExtensionController.EnableSource.USER)
        result.accept({ updated -> if (updated != null) register(updated) }, { error = "Extension state could not be changed"; emit() })
    }
    fun update(extension: WebExtension) { controller.update(extension).accept({ updated -> if (updated != null) register(updated) }, { error = "Extension could not be updated"; emit() }) }
    fun remove(extension: WebExtension) {
        if (extension.isBuiltIn) return
        controller.uninstall(extension).accept({ installed.remove(extension.id); defaultActions.remove(extension.id); emit() }, { error = "Extension could not be removed"; emit() })
    }
}
