/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.app.Activity
import android.app.AlertDialog
import android.widget.*
import com.acuteweb.core.*
import org.mozilla.geckoview.*
import java.net.URI

/** Extension documents have their own surface and strict origin boundary, never an ordinary browser tab. */
internal class ExtensionUi(private val activity: Activity, private val browser: BrowserController, private val manager: ExtensionManager, private val runtime: GeckoRuntime) {
    private var dialog: AlertDialog? = null
    private var permissionDialog: AlertDialog? = null
    private var permissionReply: ((Boolean) -> Unit)? = null
    private var session: GeckoSession? = null
    private var view: GeckoView? = null
    private val observer: () -> Unit = { refresh() }
    fun start() {
        manager.popup = ::openPopup
        manager.prompt = ::permissions
        manager.attach(observer)
    }
    fun refresh() { if (browser.tabs.mode == BrowsingMode.PRIVATE) close() }
    fun stop() { manager.detach(observer); manager.detachUi(); close() }
    private fun close() {
        permissionReply?.invoke(false); permissionReply = null
        permissionDialog?.dismiss(); permissionDialog = null
        dialog?.dismiss(); dialog = null
        view?.releaseSession(); view = null
        session?.let { if (it.isOpen) it.close() }; session = null
    }
    internal fun openPopup(extension: WebExtension): GeckoSession? {
        if (browser.tabs.mode != BrowsingMode.NORMAL || activity.isFinishing) return null
        close()
        val origin = runCatching { URI(extension.metaData?.baseUrl ?: return null) }.getOrNull() ?: return null
        val popup = GeckoSession()
        popup.navigationDelegate = object : GeckoSession.NavigationDelegate {
            override fun onLoadRequest(session: GeckoSession, request: GeckoSession.NavigationDelegate.LoadRequest): GeckoResult<AllowOrDeny> {
                val target = runCatching { URI(request.uri) }.getOrNull()
                if (target?.scheme == "moz-extension" && target.rawAuthority == origin.rawAuthority) return GeckoResult.allow()
                if (request.hasUserGesture && NavigationPolicy.allows(request.uri) && browser.tabs.mode == BrowsingMode.NORMAL) {
                    if (browser.newTab(BrowsingMode.NORMAL)) browser.navigate(request.uri)
                }
                return GeckoResult.deny()
            }
            override fun onNewSession(session: GeckoSession, uri: String): GeckoResult<GeckoSession>? = null
        }
        popup.permissionDelegate = object : GeckoSession.PermissionDelegate {
            override fun onContentPermissionRequest(session: GeckoSession, perm: GeckoSession.PermissionDelegate.ContentPermission): GeckoResult<Int> = GeckoResult.fromValue(GeckoSession.PermissionDelegate.ContentPermission.VALUE_DENY)
        }
        popup.contentDelegate = object : GeckoSession.ContentDelegate { override fun onCloseRequest(session: GeckoSession) { close() } }
        popup.printDelegate = object : GeckoSession.PrintDelegate { override fun onPrint(stream: java.io.InputStream) { runCatching { stream.close() } } }
        popup.open(runtime)
        session = popup
        val surface = GeckoView(activity).apply { isSaveEnabled = false; isSaveFromParentEnabled = false; setSession(popup) }
        view = surface
        dialog = AlertDialog.Builder(activity).setTitle(extension.metaData?.name ?: extension.id)
            .setView(surface).setNegativeButton(android.R.string.cancel) { _, _ -> close() }.create().also { panel ->
                panel.setOnCancelListener { close() }; panel.show()
                panel.window?.setLayout((activity.resources.displayMetrics.widthPixels * 0.94).toInt(), (activity.resources.displayMetrics.heightPixels * 0.72).toInt())
            }
        popup.setActive(true); popup.setFocused(true)
        return popup
    }
    private fun permissions(name: String, permissions: String, reply: (Boolean) -> Unit) {
        if (browser.tabs.mode != BrowsingMode.NORMAL || permissionDialog != null || activity.isFinishing) { reply(false); return }
        permissionReply = reply
        permissionDialog = AlertDialog.Builder(activity).setTitle(name)
            .setMessage(activity.getString(R.string.extension_permissions, permissions))
            .setPositiveButton(R.string.extension_allow) { _, _ -> permissionReply?.invoke(true); permissionReply = null }
            .setNegativeButton(android.R.string.cancel) { _, _ -> permissionReply?.invoke(false); permissionReply = null }
            .create().also { panel -> panel.setOnDismissListener { permissionReply?.invoke(false); permissionReply = null; permissionDialog = null }; panel.show() }
    }
    fun show() {
        if (browser.tabs.mode != BrowsingMode.NORMAL) return
        val items = manager.extensions
        val names = items.map { extension -> "${extension.metaData?.name ?: extension.id} · ${extension.metaData?.version.orEmpty()}${if (extension.metaData?.enabled == false) " · Disabled" else ""}" }
        AlertDialog.Builder(activity).setTitle(R.string.extensions_section).setItems(names.toTypedArray()) { _, index ->
            val extension = items[index]
            val choices = mutableListOf(activity.getString(R.string.extension_open), activity.getString(if (extension.metaData?.enabled == true) R.string.extension_disable else R.string.extension_enable), activity.getString(R.string.extension_update))
            if (extension.metaData?.optionsPageUrl != null) choices.add(activity.getString(R.string.extension_options))
            if (!extension.isBuiltIn) choices.add(activity.getString(R.string.extension_remove))
            AlertDialog.Builder(activity).setTitle(extension.metaData?.name ?: extension.id).setItems(choices.toTypedArray()) { _, action ->
                when (choices[action]) {
                    activity.getString(R.string.extension_open) -> if (!manager.click(extension.id)) toast(R.string.extension_no_action)
                    activity.getString(R.string.extension_enable), activity.getString(R.string.extension_disable) -> manager.toggle(extension)
                    activity.getString(R.string.extension_update) -> manager.update(extension)
                    activity.getString(R.string.extension_options) -> openPopup(extension)?.let { extension.metaData?.optionsPageUrl?.let(it::loadUri) }
                    activity.getString(R.string.extension_remove) -> AlertDialog.Builder(activity).setTitle(R.string.extension_remove).setMessage(R.string.extension_remove_notice)
                        .setPositiveButton(R.string.delete) { _, _ -> manager.remove(extension) }.setNegativeButton(android.R.string.cancel, null).show()
                }
            }.show()
        }.setPositiveButton(R.string.extension_install) { _, _ -> install() }.setNegativeButton(android.R.string.cancel, null)
            .setMessage(if (items.isEmpty()) manager.error ?: activity.getString(R.string.extensions_loading) else null).show()
    }
    private fun install() {
        val input = EditText(activity).apply { hint = "https://…/extension.xpi"; inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI; isSaveEnabled = false }
        AlertDialog.Builder(activity).setTitle(R.string.extension_install).setView(input).setMessage(R.string.extension_install_notice)
            .setPositiveButton(R.string.extension_install) { _, _ -> manager.install(input.text.toString().trim()) }
            .setNegativeButton(android.R.string.cancel, null).show()
    }
    private fun toast(id: Int) { Toast.makeText(activity, id, Toast.LENGTH_SHORT).show() }
}
