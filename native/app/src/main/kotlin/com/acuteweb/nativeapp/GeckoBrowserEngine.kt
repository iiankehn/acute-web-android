/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import com.acuteweb.core.BrowserEngine
import com.acuteweb.core.NavigationPolicy
import com.acuteweb.core.PageState
import org.mozilla.geckoview.*

/** Sole Gecko adapter for this slice. No Fenix source or overlay is required. */
class GeckoBrowserEngine(runtime: GeckoRuntime, private val changed: (PageState) -> Unit) : BrowserEngine {
    val session = GeckoSession(GeckoSessionSettings.Builder().useTrackingProtection(true).build())
    private var state = PageState()
    init {
        session.navigationDelegate = object : GeckoSession.NavigationDelegate {
            override fun onLocationChange(session: GeckoSession, url: String?, perms: MutableList<GeckoSession.PermissionDelegate.ContentPermission>, hasUserGesture: Boolean) {
                update(state.copy(uri = url.orEmpty(), error = null))
            }
            override fun onCanGoBack(session: GeckoSession, canGoBack: Boolean) { update(state.copy(canGoBack = canGoBack)) }
            override fun onCanGoForward(session: GeckoSession, canGoForward: Boolean) { update(state.copy(canGoForward = canGoForward)) }
            override fun onLoadRequest(session: GeckoSession, request: GeckoSession.NavigationDelegate.LoadRequest): GeckoResult<AllowOrDeny> =
                GeckoResult.fromValue(if (NavigationPolicy.allows(request.uri)) AllowOrDeny.ALLOW else AllowOrDeny.DENY)
            // Popup/new-window support requires app-owned tab routing; fail closed for now.
            override fun onNewSession(session: GeckoSession, uri: String): GeckoResult<GeckoSession>? = null
            override fun onLoadError(session: GeckoSession, uri: String?, error: WebRequestError): GeckoResult<String>? {
                update(state.copy(error = "Page could not be loaded. Check the address or connection."))
                return null
            }
        }
        session.contentDelegate = object : GeckoSession.ContentDelegate {
            override fun onTitleChange(session: GeckoSession, title: String?) { update(state.copy(title = title ?: "Acute")) }
        }
        session.permissionDelegate = object : GeckoSession.PermissionDelegate {
            override fun onContentPermissionRequest(session: GeckoSession, perm: GeckoSession.PermissionDelegate.ContentPermission): GeckoResult<Int> =
                GeckoResult.fromValue(GeckoSession.PermissionDelegate.ContentPermission.VALUE_DENY)
            // Gecko's default Android/media callbacks reject requests. No silent grants.
        }
        session.open(runtime)
    }
    private fun update(next: PageState) { state = next; changed(next) }
    override fun navigate(uri: String) { require(NavigationPolicy.allows(uri)); session.loadUri(uri) }
    override fun back() { if (state.canGoBack) session.goBack() }
    override fun forward() { if (state.canGoForward) session.goForward() }
    override fun reload() { session.reload() }
    override fun close() { session.close() }
}
