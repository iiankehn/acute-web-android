/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.app.Activity
import android.app.AlertDialog
import android.text.InputFilter
import android.widget.*
import com.acuteweb.core.BrowsingMode

/** App-owned, bounded native library controls. No normal library is displayed in private mode. */
class LibraryUi(private val activity: Activity, private val browser: BrowserController, private val places: PlacesStore) {
    private var dialog: AlertDialog? = null
    private fun available() = !activity.isFinishing && !activity.isDestroyed && browser.tabs.mode == BrowsingMode.NORMAL
    fun dismiss() { dialog?.dismiss(); dialog = null }
    private fun failed() { if (available()) Toast.makeText(activity, R.string.library_error, Toast.LENGTH_LONG).show() }
    private fun <T> consume(result: Result<T>, success: (T) -> Unit) {
        if (!available()) return
        result.onSuccess(success).onFailure { failed() }
    }
    fun bookmarkPage() {
        val page = browser.tabs.selected?.page ?: return
        if (!available() || page.uri.isEmpty()) return
        edit(null, page.uri, page.title)
    }
    private fun edit(id: String?, uri: String, title: String) {
        if (!available()) return
        dismiss()
        val layout = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; setPadding(24, 16, 24, 0) }
        val name = EditText(activity).apply { hint = activity.getString(R.string.bookmark_title); setText(title); filters = arrayOf(InputFilter.LengthFilter(512)) }
        val url = EditText(activity).apply {
            hint = activity.getString(R.string.address_hint); setText(uri); setSingleLine(true)
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
            filters = arrayOf(InputFilter.LengthFilter(4096))
        }
        layout.addView(name); layout.addView(url)
        val editor = AlertDialog.Builder(activity).setTitle(R.string.save_bookmark).setView(layout)
            .setNegativeButton(android.R.string.cancel, null).setPositiveButton(R.string.save, null).create()
        dialog = editor; editor.show()
        editor.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            if (!available()) { dismiss(); return@setOnClickListener }
            val address = url.text.toString().trim().takeIf(com.acuteweb.core.NavigationPolicy::allows)
            if (address == null || !com.acuteweb.core.NavigationPolicy.allows(address)) { url.error = activity.getString(R.string.invalid_address); return@setOnClickListener }
            editor.getButton(AlertDialog.BUTTON_POSITIVE).isEnabled = false
            val complete: (Result<*>) -> Unit = { result ->
                if (available() && dialog === editor) {
                    if (result.isSuccess) { dismiss(); Toast.makeText(activity, R.string.bookmark_saved, Toast.LENGTH_SHORT).show() }
                    else { editor.getButton(AlertDialog.BUTTON_POSITIVE).isEnabled = true; failed() }
                }
            }
            if (id == null) places.saveBookmark(BrowsingMode.NORMAL, address, name.text.toString(), complete)
            else places.editBookmark(id, address, name.text.toString(), complete)
        }
    }
    fun bookmarks() {
        if (!available()) return
        places.bookmarks { result -> consume(result) { items ->
            showList(R.string.recent_bookmarks, items.map { it.title + "\n" + it.uri },
                open = { index -> dismiss(); browser.navigate(items[index].uri) },
                actions = { index ->
                    val item = items[index]
                    dismiss()
                    dialog = AlertDialog.Builder(activity).setTitle(item.title)
                        .setItems(arrayOf(activity.getString(R.string.edit), activity.getString(R.string.delete))) { _, action ->
                            if (!available()) return@setItems
                            if (action == 0) edit(item.id, item.uri, item.title)
                            else places.deleteBookmark(item.id) { consume(it) { bookmarks() } }
                        }.create().also { it.show() }
                })
        } }
    }
    fun history() {
        if (!available()) return
        places.history { result -> consume(result) { items ->
            showList(R.string.recent_history, items.map { it.title + "\n" + it.uri },
                open = { index -> dismiss(); browser.navigate(items[index].uri) },
                actions = { index ->
                    val item = items[index]
                    dismiss()
                    dialog = AlertDialog.Builder(activity).setTitle(R.string.delete_history_page)
                        .setMessage(item.uri).setNegativeButton(android.R.string.cancel, null)
                        .setPositiveButton(R.string.delete) { _, _ ->
                            if (available()) places.deleteHistory(item.uri) { consume(it) { history() } }
                        }.create().also { it.show() }
                }, clear = {
                    dismiss()
                    dialog = AlertDialog.Builder(activity).setTitle(R.string.clear_history)
                        .setMessage(R.string.clear_history_description).setNegativeButton(android.R.string.cancel, null)
                        .setPositiveButton(R.string.delete) { _, _ ->
                            if (available()) places.clearHistory { consume(it) { history() } }
                        }.create().also { it.show() }
                })
        } }
    }
    private fun showList(title: Int, labels: List<String>, open: (Int) -> Unit, actions: (Int) -> Unit, clear: (() -> Unit)? = null) {
        if (!available()) return
        dismiss()
        val list = ListView(activity).apply {
            adapter = ArrayAdapter(activity, android.R.layout.simple_list_item_1, labels.ifEmpty { listOf(activity.getString(R.string.library_empty)) })
            setOnItemClickListener { _, _, index, _ -> if (labels.isNotEmpty() && available()) open(index) }
            setOnItemLongClickListener { _, _, index, _ -> if (labels.isNotEmpty() && available()) actions(index); true }
        }
        val builder = AlertDialog.Builder(activity).setTitle(title).setView(list).setNegativeButton(android.R.string.cancel, null)
        if (clear != null) builder.setNeutralButton(R.string.clear_history) { _, _ -> if (available()) clear() }
        dialog = builder.create().also { it.show() }
    }
}
