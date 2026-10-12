/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.view.WindowManager
import android.widget.ArrayAdapter
import android.widget.ListView
import android.widget.Toast
import com.acuteweb.core.BrowsingMode

class DownloadUi(private val activity: Activity, private val browser: BrowserController, private val downloads: DownloadController) {
    companion object { const val CREATE_DOWNLOAD = 102 }
    private var dialog: AlertDialog? = null
    private var offeredId: String? = null
    private var list: ListView? = null
    private var listMode: BrowsingMode? = null
    private var started = false
    private val listener = { refresh() }
    fun start() { started = true; downloads.attach(listener) }
    fun stop() { started = false; downloads.detach(listener); dismiss() }
    private fun dismiss() { dialog?.dismiss(); dialog = null; offeredId = null; list = null; listMode = null }
    fun refresh() {
        if (!started || activity.isFinishing || activity.isDestroyed) return
        if (listMode != null && listMode != browser.tabs.mode) dismiss()
        list?.adapter = ArrayAdapter(activity, android.R.layout.simple_list_item_1, labels())
        val offer = downloads.offer?.takeIf { it.mode == browser.tabs.mode && it.status == DownloadController.Status.OFFERED }
        if (offeredId != null && offeredId != offer?.id) dismiss()
        if (offer == null || offeredId == offer.id || list != null) return
        dismiss(); offeredId = offer.id
        val builder = AlertDialog.Builder(activity).setTitle(offer.name)
            .setMessage(if (offer.mode == BrowsingMode.PRIVATE) R.string.private_download_notice else R.string.download_notice)
            .setNegativeButton(android.R.string.cancel) { _, _ -> downloads.cancel(offer.id) }
            .setPositiveButton(R.string.save) { _, _ ->
                dialog = null; offeredId = null
                if (downloads.choose(offer.id)) {
                    val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE); type = offer.mime
                        putExtra(Intent.EXTRA_TITLE, offer.name)
                    }
                    runCatching { activity.startActivityForResult(intent, CREATE_DOWNLOAD) }.onFailure {
                        downloads.finishPicker(null); Toast.makeText(activity, R.string.download_picker_missing, Toast.LENGTH_LONG).show()
                    }
                }
            }
        dialog = builder.create().also { popup ->
            if (offer.mode == BrowsingMode.PRIVATE) popup.window?.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
            watchDismiss(popup)
            popup.setOnCancelListener { downloads.cancel(offer.id) }; popup.show()
        }
    }
    fun result(resultCode: Int, data: Intent?) {
        val mode = downloads.offer?.mode
        val success = downloads.finishPicker(if (resultCode == Activity.RESULT_OK) data?.data else null)
        if (!success && resultCode == Activity.RESULT_OK) Toast.makeText(activity, R.string.download_interrupted, Toast.LENGTH_LONG).show()
        if (success && resultCode == Activity.RESULT_OK && mode == browser.tabs.mode) show() else refresh()
    }
    fun finish() { downloads.abandonPicker() }
    private fun watchDismiss(popup: AlertDialog) {
        popup.setOnDismissListener {
            if (dialog === popup) { dialog = null; offeredId = null; list = null; listMode = null }
        }
    }
    private fun labels() = downloads.visible(browser.tabs.mode).map { item ->
        item.name + "\n" + activity.getString(when (item.status) {
            DownloadController.Status.OFFERED -> R.string.download_waiting
            DownloadController.Status.CHOOSING -> R.string.download_choosing
            DownloadController.Status.SAVING -> R.string.download_saving
            DownloadController.Status.CANCELLING -> R.string.download_cancelling
            DownloadController.Status.COMPLETE -> R.string.download_complete
            DownloadController.Status.FAILED -> R.string.download_failed
            DownloadController.Status.CANCELLED -> R.string.download_cancelled
        }, item.bytes)
    }.ifEmpty { listOf(activity.getString(R.string.downloads_empty)) }
    fun show() {
        dismiss(); listMode = browser.tabs.mode
        list = ListView(activity).apply {
            adapter = ArrayAdapter(activity, android.R.layout.simple_list_item_1, labels())
            setOnItemClickListener { _, _, index, _ ->
                val item = downloads.visible(browser.tabs.mode).getOrNull(index) ?: return@setOnItemClickListener
                when (item.status) {
                    DownloadController.Status.COMPLETE -> item.destination?.let { open(it, item.mime) }
                    DownloadController.Status.OFFERED -> { dismiss(); refresh() }
                    DownloadController.Status.CHOOSING, DownloadController.Status.SAVING, DownloadController.Status.CANCELLING -> downloads.cancel(item.id)
                    else -> Unit
                }
            }
        }
        dialog = AlertDialog.Builder(activity).setTitle(R.string.downloads_session).setView(list)
            .setNegativeButton(android.R.string.cancel, null).create().also { popup ->
                if (browser.tabs.mode == BrowsingMode.PRIVATE) popup.window?.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
                watchDismiss(popup); popup.show()
            }
    }
    private fun open(uri: Uri, mime: String) {
        val intent = Intent(Intent.ACTION_VIEW).setDataAndType(uri, mime).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        runCatching { activity.startActivity(Intent.createChooser(intent, activity.getString(R.string.open_download))) }
            .onFailure { Toast.makeText(activity, R.string.download_open_failed, Toast.LENGTH_LONG).show() }
    }
}
