/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.content.Context
import android.graphics.pdf.PdfRenderer
import android.os.*
import android.print.*
import com.acuteweb.core.DownloadPolicy
import java.io.*
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Gecko-generated document, copied without re-rendering; Android's spooler selects printed pages. */
internal class PdfPrintAdapter(internal val file: File, private val name: String, val pageCount: Int) : PrintDocumentAdapter() {
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private val finished = AtomicBoolean(false)
    internal val closed get() = finished.get()
    @Volatile private var output: OutputStream? = null
    override fun onLayout(oldAttributes: PrintAttributes?, newAttributes: PrintAttributes?, signal: CancellationSignal,
                          callback: LayoutResultCallback, extras: Bundle?) {
        if (finished.get() || signal.isCanceled) callback.onLayoutCancelled()
        else callback.onLayoutFinished(PrintDocumentInfo.Builder(name).setContentType(PrintDocumentInfo.CONTENT_TYPE_DOCUMENT)
            .setPageCount(pageCount).build(), oldAttributes != newAttributes)
    }
    override fun onWrite(pages: Array<out PageRange>, destination: ParcelFileDescriptor, signal: CancellationSignal, callback: WriteResultCallback) {
        write(destination, signal) { result ->
            when {
                signal.isCanceled || finished.get() -> callback.onWriteCancelled()
                result.isSuccess -> callback.onWriteFinished(arrayOf(PageRange.ALL_PAGES))
                else -> callback.onWriteFailed("Could not write the document")
            }
        }
    }
    /** Same descriptor/resource path used by Android printing and instrumentation. */
    internal fun write(destination: ParcelFileDescriptor, signal: CancellationSignal, callback: (Result<Long>) -> Unit) {
        if (finished.get()) { destination.close(); main.post { callback(Result.failure(InterruptedIOException())) }; return }
        signal.setOnCancelListener { closeOutput() }
        io.execute {
            val result = runCatching {
                val sink = ParcelFileDescriptor.AutoCloseOutputStream(destination)
                output = sink
                try { DownloadPolicy.copy(FileInputStream(file), sink, file.length(), { finished.get() || signal.isCanceled }) }
                finally { runCatching { sink.close() }; output = null }
            }
            runCatching { destination.close() }
            main.post { callback(result) }
        }
    }
    private fun closeOutput() { Thread({ runCatching { output?.close() } }, "acute-print-cancel").apply { isDaemon = true; start() } }
    override fun onFinish() {
        if (finished.getAndSet(true)) return
        closeOutput(); io.execute { file.delete() }; io.shutdown()
    }
    companion object {
        const val MAX_PRINT_BYTES = 64L * 1024 * 1024
        private fun directory(context: Context) = File(context.cacheDir, "acute-print")
        fun clearAbandoned(context: Context) { directory(context).listFiles()?.filter { it.isFile }?.forEach { it.delete() } }
        /** Explicit Print consent permits this temporary app cache and system spooler export. */
        fun prepare(context: Context, stream: InputStream, name: String, cancelled: () -> Boolean): PdfPrintAdapter {
            var file: File? = null
            try {
                val dir = directory(context); check(dir.isDirectory || dir.mkdirs())
                file = File.createTempFile("document-", ".pdf", dir)
                val sink = object : FilterOutputStream(FileOutputStream(file)) {
                    private var bytes = 0L
                    override fun write(buffer: ByteArray, offset: Int, count: Int) {
                        if (bytes + count > MAX_PRINT_BYTES) throw IOException("Print document exceeds 64 MiB")
                        out.write(buffer, offset, count); bytes += count
                    }
                }
                DownloadPolicy.copy(stream, sink, cancelled = cancelled)
                if (cancelled()) throw InterruptedIOException()
                val count = PdfRenderer(ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)).use { it.pageCount }
                check(count > 0)
                return PdfPrintAdapter(file, name, count)
            } catch (error: Throwable) { runCatching { stream.close() }; file?.delete(); throw error }
        }
    }
}
