/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.app.Activity
import android.app.AlertDialog
import android.content.pm.PackageManager
import android.print.PrintManager
import android.view.WindowManager
import android.widget.Toast
import com.acuteweb.core.*
import org.mozilla.geckoview.WebResponse
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Activity-bound generation. A cancelled/replaced request closes any late Gecko response. */
internal class DocumentUi(private val activity: Activity, private val browser: BrowserController, private val downloads: DownloadController) {
    private val io = Executors.newSingleThreadExecutor()
    private var dialog: AlertDialog? = null
    private var cancelled: AtomicBoolean? = null
    @Volatile private var generatingStream: java.io.InputStream? = null
    private var tabId: String? = null
    private var pageUri: String? = null
    val printAvailable get() = !activity.packageManager.hasSystemFeature(PackageManager.FEATURE_AUTOMOTIVE) &&
        activity.packageManager.hasSystemFeature(PackageManager.FEATURE_PRINTING) && activity.getSystemService(PrintManager::class.java) != null
    fun refresh() { if (tabId != null && (browser.tabs.selected?.id != tabId || browser.tabs.selected?.page?.uri != pageUri)) cancel() }
    fun stop() { cancel() }
    fun destroy() { cancel(); io.shutdown() }
    private fun cancel() {
        cancelled?.set(true); cancelled = null; tabId = null; pageUri = null; dialog?.dismiss(); dialog = null
        val stream = generatingStream; generatingStream = null
        if (stream != null) Thread({ runCatching { stream.close() } }, "acute-document-cancel").apply { isDaemon = true; start() }
    }
    fun export(print: Boolean = false) {
        if (cancelled != null || dialog != null || (print && !printAvailable)) return
        val tab = browser.tabs.selected ?: return
        if (!NavigationPolicy.allows(tab.page.uri) || downloads.busy) { toast(R.string.document_unavailable); return }
        if (print && tab.mode == BrowsingMode.PRIVATE) {
            tabId = tab.id; pageUri = tab.page.uri
            dialog = AlertDialog.Builder(activity).setTitle(R.string.print_page).setMessage(R.string.private_print_notice)
                .setNegativeButton(android.R.string.cancel, null).setPositiveButton(R.string.print_page) { _, _ ->
                    dialog = null
                    if (browser.tabs.selected?.id == tab.id) generate(true)
                }.create().also { popup ->
                    popup.window?.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
                    popup.setOnDismissListener { if (dialog === popup) dialog = null }; popup.show()
                }
        } else generate(print)
    }
    private fun generate(print: Boolean) {
        val tab = browser.tabs.selected ?: return
        val engine = browser.selectedEngine() ?: return
        val token = AtomicBoolean(false); cancelled = token; tabId = tab.id; pageUri = tab.page.uri
        val filename = DownloadPolicy.filename(tab.page.title).removeSuffix(".pdf").take(110) + ".pdf"
        dialog = AlertDialog.Builder(activity).setTitle(R.string.document_preparing)
            .setMessage(R.string.document_preparing_notice).setNegativeButton(android.R.string.cancel) { _, _ -> cancel() }
            .create().also { popup ->
                if (tab.mode == BrowsingMode.PRIVATE) popup.window?.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
                popup.setOnCancelListener { cancel() }; popup.show()
            }
        engine.pdf { result ->
            if (token.get()) { runCatching { result.getOrNull()?.close() }; return@pdf }
            val stream = result.getOrNull()
            if (stream == null) { cancel(); toast(R.string.document_failed); return@pdf }
            if (!print) {
                cancel()
                val response = WebResponse.Builder(tab.page.uri).statusCode(200).body(stream)
                    .header("Content-Type", "application/pdf")
                    .header("Content-Disposition", "attachment; filename=\"${filename.replace('"', '_')}\"").build()
                if (!downloads.receive(tab.mode, response)) toast(R.string.document_failed)
            } else {
                generatingStream = stream
                io.execute {
                    val prepared = runCatching { PdfPrintAdapter.prepare(activity.applicationContext, stream, filename, token::get) }
                    if (generatingStream === stream) generatingStream = null
                    activity.runOnUiThread {
                        if (token.get()) { prepared.getOrNull()?.onFinish(); return@runOnUiThread }
                        cancel()
                        prepared.onSuccess { adapter ->
                            runCatching { activity.getSystemService(PrintManager::class.java).print(filename, adapter, null) }
                                .onFailure { adapter.onFinish(); toast(R.string.document_failed) }
                        }.onFailure { toast(R.string.document_failed) }
                    }
                }
            }
        }
    }
    private fun toast(message: Int) { Toast.makeText(activity, message, Toast.LENGTH_LONG).show() }
}
