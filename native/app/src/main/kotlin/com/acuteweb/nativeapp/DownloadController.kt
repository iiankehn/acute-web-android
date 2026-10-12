/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.content.Context
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.CancellationSignal
import android.os.ParcelFileDescriptor
import android.webkit.URLUtil
import com.acuteweb.core.BrowsingMode
import com.acuteweb.core.DownloadPolicy
import com.acuteweb.core.NavigationPolicy
import org.mozilla.geckoview.WebResponse
import java.io.InputStream
import java.io.Closeable
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Process-owned transfer state only. Files are written only after explicit destination selection. */
class DownloadController(context: Context) {
    enum class Status { OFFERED, CHOOSING, SAVING, CANCELLING, COMPLETE, FAILED, CANCELLED }
    data class Item(val id: String, val mode: BrowsingMode, val name: String, val mime: String,
                    val status: Status, val bytes: Long = 0, val destination: Uri? = null)
    private class Transfer(val id: String, val body: InputStream, val expected: Long?) {
        val cancelled = AtomicBoolean(false)
        val signal = CancellationSignal()
        @Volatile var output: Closeable? = null
    }
    private val resolver = context.applicationContext.contentResolver
    private val main = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor()
    private val closer = Executors.newSingleThreadExecutor()
    private val items = linkedMapOf<String, Item>()
    private val listeners = linkedSetOf<() -> Unit>()
    private var pickerOwner: String? = null
    private var pending: Transfer? = null
    private var active: Transfer? = null
    private var expiry: Runnable? = null
    val busy get() = pending != null || active != null || pickerOwner != null
    val offer get() = pending?.let { items[it.id] }
    fun visible(mode: BrowsingMode): List<Item> { checkThread(); return items.values.filter { it.mode == mode }.reversed() }
    private fun checkThread() { check(Looper.myLooper() == Looper.getMainLooper()) }
    fun attach(listener: () -> Unit) { checkThread(); listeners.add(listener); listener() }
    fun detach(listener: () -> Unit) { checkThread(); listeners.remove(listener) }
    private fun emit() { listeners.toList().forEach { it() } }
    private fun update(id: String, change: (Item) -> Item) { items[id]?.let { items[id] = change(it); emit() } }
    fun receive(mode: BrowsingMode, response: WebResponse): Boolean {
        checkThread()
        val body = response.body
        val length = response.headers["content-length"]?.toLongOrNull()?.takeIf { it >= 0 }
        if (body == null || response.statusCode != 200 || !NavigationPolicy.allows(response.uri) ||
            response.uri.length > 4096 || (length != null && length > DownloadPolicy.MAX_BYTES) || pending != null || active != null || pickerOwner != null) {
            runCatching { body?.close() }; return false
        }
        response.setReadTimeoutMillis(30_000)
        val mime = DownloadPolicy.mime(response.headers["content-type"])
        val name = DownloadPolicy.filename(URLUtil.guessFileName(response.uri, response.headers["content-disposition"]?.take(4096), mime))
        val id = UUID.randomUUID().toString()
        items.values.filter { it.mode == mode }.take((items.values.count { it.mode == mode } - 19).coerceAtLeast(0)).forEach { items.remove(it.id) }
        items[id] = Item(id, mode, name, mime, Status.OFFERED)
        pending = Transfer(id, body, length.takeIf { response.headers["content-encoding"].orEmpty().let { encoding -> encoding.isEmpty() || encoding.equals("identity", true) } })
        // The unread Gecko channel stays suspended. Bound even an abandoned file picker.
        expiry = Runnable { if (pending?.id == id) cancel(id) }.also { main.postDelayed(it, 120_000) }
        emit(); return true
    }
    fun choose(id: String): Boolean {
        checkThread(); if (pending?.id != id || pickerOwner != null || items[id]?.status != Status.OFFERED) return false
        pickerOwner = id; update(id) { it.copy(status = Status.CHOOSING) }; return true
    }
    fun finishPicker(destination: Uri?): Boolean {
        checkThread(); val id = pickerOwner ?: return false
        pickerOwner = null
        if (destination == null) { cancel(id); return true }
        return save(id, destination)
    }
    fun abandonPicker() {
        checkThread(); pickerOwner = null; pending?.id?.let(::cancel)
    }
    private fun save(id: String, destination: Uri): Boolean {
        checkThread()
        val transfer = pending?.takeIf { it.id == id } ?: return false
        if (items[id]?.status != Status.CHOOSING || destination.scheme != "content") { cancel(id); return false }
        expiry?.let(main::removeCallbacks); expiry = null
        pending = null; active = transfer
        update(id) { it.copy(status = Status.SAVING, destination = destination) }
        io.execute {
            var lastProgress = 0L
            var handedOff = false
            val result = runCatching {
                try {
                    val descriptor = resolver.openFileDescriptor(destination, "w", transfer.signal) ?: error("No destination")
                    val output = ParcelFileDescriptor.AutoCloseOutputStream(descriptor)
                    transfer.output = output; handedOff = true
                    DownloadPolicy.copy(transfer.body, output, transfer.expected, transfer.cancelled::get) { count ->
                        val now = System.nanoTime()
                        if (now - lastProgress >= 100_000_000) {
                            lastProgress = now
                            main.post { update(id) { item -> item.copy(bytes = count) } }
                        }
                    }
                } finally { if (!handedOff) runCatching { transfer.body.close() } }
            }
            transfer.output = null
            main.post {
                if (active === transfer) active = null
                update(id) { item -> item.copy(status = if (transfer.cancelled.get()) Status.CANCELLED else if (result.isSuccess) Status.COMPLETE else Status.FAILED,
                    bytes = result.getOrNull() ?: item.bytes) }
            }
        }
        return true
    }
    fun cancel(id: String) {
        checkThread()
        pending?.takeIf { it.id == id }?.let {
            expiry?.let(main::removeCallbacks); expiry = null; pending = null
            it.cancelled.set(true); runCatching { it.body.close() }
            update(id) { item -> item.copy(status = Status.CANCELLED) }; return
        }
        active?.takeIf { it.id == id }?.let { transfer ->
            transfer.cancelled.set(true)
            update(id) { it.copy(status = Status.CANCELLING) }
            closer.execute { transfer.signal.cancel(); runCatching { transfer.body.close() }; runCatching { transfer.output?.close() } }
        }
    }
    fun forgetPrivate() {
        checkThread(); items.values.filter { it.mode == BrowsingMode.PRIVATE }.map { it.id }.forEach(::cancel)
        items.entries.removeAll { it.value.mode == BrowsingMode.PRIVATE }; emit()
    }
    internal fun shutdown() {
        checkThread(); abandonPicker(); items.keys.toList().forEach(::cancel); items.clear(); listeners.clear(); io.shutdown(); closer.shutdown()
    }
}
