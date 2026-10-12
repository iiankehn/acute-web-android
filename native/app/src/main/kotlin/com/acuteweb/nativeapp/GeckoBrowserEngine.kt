/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import com.acuteweb.core.BrowsingMode
import com.acuteweb.core.BrowserEngine
import com.acuteweb.core.NavigationPolicy
import com.acuteweb.core.PageState
import org.mozilla.geckoview.*

/** Gecko session lifecycle/state belongs here, outside product selection/storage policy. */
class GeckoBrowserEngine(
    private val runtime: GeckoRuntime,
    private val privateMode: Boolean,
    privateContext: String?,
    initial: PageState,
    private val changed: (PageState) -> Unit,
    private val snapshot: (String?) -> Unit,
    private val newWindow: (String) -> GeckoSession?,
    private val closeWindow: () -> Unit,
    private val history: PlacesStore? = null,
    private val linkContext: (String) -> Unit = {},
    private val downloadResponse: ((BrowsingMode, WebResponse) -> Boolean)? = null,
) : BrowserEngine {
    val session = GeckoSession(GeckoSessionSettings.Builder().useTrackingProtection(true)
        .usePrivateMode(privateMode).contextId(if (privateMode) privateContext else null).build())
    private var state = initial
    private var savedState: String? = null
    private var disposed = false
    private var active = false
    init {
        // Only app-owned explicit actions may export to Android. Do not install GeckoView's fallback printer.
        session.printDelegate = object : GeckoSession.PrintDelegate {
            override fun onPrint(pdfInputStream: java.io.InputStream) { runCatching { pdfInputStream.close() } }
            override fun onPrintWithStatus(pdfInputStream: java.io.InputStream): GeckoResult<Boolean> {
                runCatching { pdfInputStream.close() }
                return GeckoResult.fromException(IllegalStateException("Use Acute's explicit Print action"))
            }
        }
        session.navigationDelegate = object : GeckoSession.NavigationDelegate {
            override fun onLocationChange(session: GeckoSession, url: String?, perms: MutableList<GeckoSession.PermissionDelegate.ContentPermission>, hasUserGesture: Boolean) {
                if (url != state.uri) savedState = null
                update(state.copy(uri = url.orEmpty(), error = null))
            }
            override fun onCanGoBack(session: GeckoSession, canGoBack: Boolean) { update(state.copy(canGoBack = canGoBack)) }
            override fun onCanGoForward(session: GeckoSession, canGoForward: Boolean) { update(state.copy(canGoForward = canGoForward)) }
            override fun onLoadRequest(session: GeckoSession, request: GeckoSession.NavigationDelegate.LoadRequest): GeckoResult<AllowOrDeny> {
                val permitted = NavigationPolicy.allowsOrBlank(request.uri) &&
                    (request.target != GeckoSession.NavigationDelegate.TARGET_WINDOW_NEW || request.hasUserGesture)
                return GeckoResult.fromValue(if (permitted) AllowOrDeny.ALLOW else AllowOrDeny.DENY)
            }
            override fun onNewSession(session: GeckoSession, uri: String): GeckoResult<GeckoSession>? =
                if (!disposed && NavigationPolicy.allowsOrBlank(uri)) newWindow(uri)?.let { GeckoResult.fromValue(it) } else null
            override fun onLoadError(session: GeckoSession, uri: String?, error: WebRequestError): GeckoResult<String>? {
                update(state.copy(error = "Page could not be loaded. Check the address or connection.")); return null
            }
        }
        session.contentDelegate = object : GeckoSession.ContentDelegate {
            override fun onTitleChange(session: GeckoSession, title: String?) {
                if (!disposed && title != null) history?.updateTitle(mode, state.uri, title)
                update(state.copy(title = title ?: "Acute"))
            }
            override fun onContextMenu(session: GeckoSession, screenX: Int, screenY: Int, element: GeckoSession.ContentDelegate.ContextElement) {
                if (!disposed) element.linkUri?.takeIf { it.length <= 4096 && NavigationPolicy.allows(it) }?.let(linkContext)
            }
            override fun onExternalResponse(session: GeckoSession, response: WebResponse) {
                if (!disposed && downloadResponse != null) {
                    if (!downloadResponse.invoke(mode, response)) update(state.copy(error = "Download could not start. Another transfer may be active, or this response is unsupported."))
                } else {
                    runCatching { response.body?.close() }
                    update(state.copy(error = "Download could not be started."))
                }
            }
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
        session.historyDelegate = object : GeckoSession.HistoryDelegate {
            override fun onVisited(session: GeckoSession, url: String, lastVisitedURL: String?, flags: Int): GeckoResult<Boolean> {
                val result = GeckoResult<Boolean>()
                if (disposed || history == null || flags and GeckoSession.HistoryDelegate.VISIT_TOP_LEVEL == 0 ||
                    flags and GeckoSession.HistoryDelegate.VISIT_UNRECOVERABLE_ERROR != 0) return GeckoResult.fromValue(false)
                history.recordVisit(mode, url,
                    redirect = flags and (GeckoSession.HistoryDelegate.VISIT_REDIRECT_TEMPORARY or GeckoSession.HistoryDelegate.VISIT_REDIRECT_PERMANENT) != 0,
                    permanent = flags and (GeckoSession.HistoryDelegate.VISIT_REDIRECT_PERMANENT or GeckoSession.HistoryDelegate.VISIT_REDIRECT_SOURCE_PERMANENT) != 0,
                    source = flags and (GeckoSession.HistoryDelegate.VISIT_REDIRECT_SOURCE or GeckoSession.HistoryDelegate.VISIT_REDIRECT_SOURCE_PERMANENT) != 0) { result.complete(it.getOrDefault(false)) }
                return result
            }
            override fun getVisited(session: GeckoSession, urls: Array<out String>): GeckoResult<BooleanArray> {
                if (disposed || history == null) return GeckoResult.fromValue(BooleanArray(urls.size))
                val result = GeckoResult<BooleanArray>()
                history.visited(mode, urls.toList()) { result.complete(it.getOrDefault(BooleanArray(urls.size))) }
                return result
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
    private val mode get() = if (privateMode) BrowsingMode.PRIVATE else BrowsingMode.NORMAL
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
    /** Gecko owns document layout and original PDF retrieval. Callbacks run on the session thread. */
    fun pdf(callback: (Result<java.io.InputStream>) -> Unit) {
        if (disposed || !session.isOpen) { callback(Result.failure(IllegalStateException("Closed tab"))); return }
        runCatching { session.saveAsPdf().accept({ stream ->
            if (disposed) { runCatching { stream?.close() }; callback(Result.failure(IllegalStateException("Closed tab"))) }
            else if (stream == null) callback(Result.failure(IllegalStateException("No document")))
            else callback(Result.success(stream))
        }, { error -> callback(Result.failure(error ?: IllegalStateException("Document generation failed"))) }) }.onFailure { callback(Result.failure(it)) }
    }
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
        session.progressDelegate = null; session.permissionDelegate = null; session.historyDelegate = null
        session.printDelegate = null
        if (session.isOpen) session.close()
    }
}
