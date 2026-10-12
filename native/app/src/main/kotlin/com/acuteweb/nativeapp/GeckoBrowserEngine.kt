/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import com.acuteweb.core.BrowserEngine
import com.acuteweb.core.NavigationPolicy
import com.acuteweb.core.PageState
import org.mozilla.geckoview.*

/** Gecko session lifecycle/state belongs here, outside product selection/storage policy. */
class GeckoBrowserEngine(
    private val runtime: GeckoRuntime,
    privateMode: Boolean,
    privateContext: String?,
    initial: PageState,
    private val changed: (PageState) -> Unit,
    private val snapshot: (String?) -> Unit,
    private val newWindow: (String) -> GeckoSession?,
    private val closeWindow: () -> Unit,
) : BrowserEngine {
    val session = GeckoSession(GeckoSessionSettings.Builder().useTrackingProtection(true)
        .usePrivateMode(privateMode).contextId(if (privateMode) privateContext else null).build())
    private var state = initial
    private var savedState: String? = null
    private var disposed = false
    private var active = false
    init {
        session.navigationDelegate = object : GeckoSession.NavigationDelegate {
            override fun onLocationChange(session: GeckoSession, url: String?, perms: MutableList<GeckoSession.PermissionDelegate.ContentPermission>, hasUserGesture: Boolean) {
                if (url != state.uri) savedState = null
                update(state.copy(uri = url.orEmpty(), error = null))
            }
            override fun onCanGoBack(session: GeckoSession, canGoBack: Boolean) { update(state.copy(canGoBack = canGoBack)) }
            override fun onCanGoForward(session: GeckoSession, canGoForward: Boolean) { update(state.copy(canGoForward = canGoForward)) }
            override fun onLoadRequest(session: GeckoSession, request: GeckoSession.NavigationDelegate.LoadRequest): GeckoResult<AllowOrDeny> {
                val permitted = NavigationPolicy.allows(request.uri) &&
                    (request.target != GeckoSession.NavigationDelegate.TARGET_WINDOW_NEW || request.hasUserGesture)
                return GeckoResult.fromValue(if (permitted) AllowOrDeny.ALLOW else AllowOrDeny.DENY)
            }
            override fun onNewSession(session: GeckoSession, uri: String): GeckoResult<GeckoSession>? =
                if (!disposed && NavigationPolicy.allows(uri)) newWindow(uri)?.let { GeckoResult.fromValue(it) } else null
            override fun onLoadError(session: GeckoSession, uri: String?, error: WebRequestError): GeckoResult<String>? {
                update(state.copy(error = "Page could not be loaded. Check the address or connection.")); return null
            }
        }
        session.contentDelegate = object : GeckoSession.ContentDelegate {
            override fun onTitleChange(session: GeckoSession, title: String?) { update(state.copy(title = title ?: "Acute")) }
            override fun onCloseRequest(session: GeckoSession) { if (!disposed) closeWindow() }
            override fun onCrash(session: GeckoSession) { lostProcess() }
            override fun onKill(session: GeckoSession) { lostProcess() }
        }
        session.progressDelegate = object : GeckoSession.ProgressDelegate {
            override fun onSessionStateChange(session: GeckoSession, sessionState: GeckoSession.SessionState) {
                if (disposed) return
                savedState = sessionState.toString()
                snapshot(savedState)
            }
        }
        session.permissionDelegate = object : GeckoSession.PermissionDelegate {
            override fun onContentPermissionRequest(session: GeckoSession, perm: GeckoSession.PermissionDelegate.ContentPermission): GeckoResult<Int> =
                GeckoResult.fromValue(GeckoSession.PermissionDelegate.ContentPermission.VALUE_DENY)
        }
    }
    fun open(restoredState: String?) {
        check(!disposed)
        savedState = restoredState
        session.open(runtime); session.setActive(false); active = false
        restoreOrLoad()
    }
    private fun restoreOrLoad() {
        val restored = runCatching { savedState?.let(GeckoSession.SessionState::fromString) }.getOrNull()
        if (restored != null && runCatching { session.restoreState(restored) }.isSuccess) return
        if (savedState != null) { savedState = null; snapshot(null) }
        if (NavigationPolicy.allows(state.uri)) session.loadUri(state.uri)
    }
    private fun lostProcess() {
        active = false
        update(state.copy(canGoBack = false, canGoForward = false, error = "This tab stopped. Reload to restore it."))
    }
    private fun ensureOpen() {
        if (!session.isOpen) { session.open(runtime); restoreOrLoad() }
    }
    fun visibility(visible: Boolean) {
        if (!session.isOpen || active == visible) return
        active = visible; session.setActive(visible); session.setFocused(visible)
    }
    fun flush() { if (!disposed && session.isOpen) session.flushSessionState() }
    private fun update(next: PageState) { if (!disposed) { state = next; changed(next) } }
    override fun navigate(uri: String) {
        require(NavigationPolicy.allows(uri)); ensureOpen()
        savedState = null; snapshot(null)
        update(state.copy(uri = uri, error = null, canGoForward = false))
        session.loadUri(uri)
    }
    override fun back() { if (session.isOpen && state.canGoBack) session.goBack() }
    override fun forward() { if (session.isOpen && state.canGoForward) session.goForward() }
    override fun reload() {
        val closed = !session.isOpen
        ensureOpen(); update(state.copy(error = null))
        if (!closed) session.reload()
    }
    override fun close() {
        disposed = true
        session.navigationDelegate = null; session.contentDelegate = null
        session.progressDelegate = null; session.permissionDelegate = null
        if (session.isOpen) session.close()
    }
}
