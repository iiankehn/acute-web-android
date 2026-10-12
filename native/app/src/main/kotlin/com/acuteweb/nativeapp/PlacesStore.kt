/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.os.Handler
import android.os.Looper
import com.acuteweb.core.BrowsingMode
import com.acuteweb.core.NavigationPolicy
import mozilla.appservices.places.uniffi.*
import java.io.File
import java.util.concurrent.Executors

/** Narrow boundary over Mozilla's maintained Rust Places schema. No account or Sync initialization. */
class PlacesStore(context: Context, name: String = "places.sqlite") {
    data class Bookmark(val id: String, val uri: String, val title: String)
    data class Visit(val uri: String, val title: String, val at: Long)
    private val file = File(context.applicationContext.noBackupFilesDir, name.also {
        require(it.matches(Regex("[a-zA-Z0-9-]+\\.sqlite")))
    })
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var api: PlacesApi? = null
    private var connection: PlacesConnection? = null
    private var openingError: Throwable? = null
    private var closed = false
    var hasError = false
        private set
    private val listeners = linkedSetOf<() -> Unit>()
    fun attach(listener: () -> Unit) { check(Looper.myLooper() == Looper.getMainLooper()); listeners.add(listener) }
    fun detach(listener: () -> Unit) { check(Looper.myLooper() == Looper.getMainLooper()); listeners.remove(listener) }

    private fun db(): PlacesConnection {
        check(!closed)
        openingError?.let { throw it }
        connection?.let { return it }
        try {
            // Places automatically recreates corrupt databases. Check the existing file first,
            // using READONLY and a no-op corruption handler (Android's default deletes files).
            if (file.exists()) {
                require(file.length() >= 100) { "Existing Places file is incomplete" }
                SQLiteDatabase.openDatabase(file.canonicalPath, null,
                    SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS,
                    { _ -> }).use { inspection ->
                    inspection.rawQuery("PRAGMA quick_check", null).use { rows ->
                        check(rows.moveToFirst() && rows.getString(0) == "ok" && !rows.moveToNext()) {
                            "Existing Places database failed its integrity check"
                        }
                    }
                }
            }
            val opened = placesApiNew(file.canonicalPath)
            api = opened
            return opened.newConnection(ConnectionType.READ_WRITE).also { connection = it }
        } catch (e: Exception) {
            // Never reset/delete a database that failed to open.
            openingError = e; throw e
        }
    }
    private fun <T> submit(callback: (Result<T>) -> Unit, action: () -> T) {
        io.execute {
            val result = runCatching(action)
            main.post {
                if (hasError != result.isFailure) {
                    hasError = result.isFailure; listeners.toList().forEach { it() }
                }
                callback(result)
            }
        }
    }
    private fun valid(uri: String) = uri.length <= 4096 && NavigationPolicy.allows(uri)
    fun recordVisit(mode: BrowsingMode, uri: String, redirect: Boolean = false,
                    permanent: Boolean = false, source: Boolean = false,
                    callback: (Result<Boolean>) -> Unit = {}) {
        if (mode == BrowsingMode.PRIVATE || !valid(uri)) { callback(Result.success(false)); return }
        submit(callback) {
            db().applyObservation(VisitObservation(url = uri,
                visitType = if (redirect) { if (permanent) VisitType.REDIRECT_PERMANENT else VisitType.REDIRECT_TEMPORARY } else VisitType.LINK,
                isRedirectSource = source, isPermanentRedirectSource = source && permanent, isRemote = false))
            true
        }
    }
    fun updateTitle(mode: BrowsingMode, uri: String, title: String) {
        if (mode == BrowsingMode.PRIVATE || !valid(uri)) return
        submit({}) { db().applyObservation(VisitObservation(uri, title.take(512), null)) }
    }
    fun visited(mode: BrowsingMode, uris: List<String>, callback: (Result<BooleanArray>) -> Unit) {
        // Never query the normal database from a private page, even for link coloring.
        if (mode == BrowsingMode.PRIVATE) { callback(Result.success(BooleanArray(uris.size))); return }
        if (uris.size > 4096) { callback(Result.success(BooleanArray(uris.size))); return }
        submit(callback) {
            val permitted = uris.withIndex().filter { valid(it.value) }
            val known = if (permitted.isEmpty()) emptyList() else db().getVisited(permitted.map { it.value })
            BooleanArray(uris.size).also { result -> permitted.forEachIndexed { i, entry -> result[entry.index] = known.getOrElse(i) { false } } }
        }
    }
    fun history(callback: (Result<List<Visit>>) -> Unit) = submit(callback) {
        db().getVisitPage(0, 100, 0).filter { !it.isHidden && valid(it.url) }
            .map { Visit(it.url, it.title.orEmpty().ifEmpty { it.url }, it.timestamp) }
    }
    fun deleteHistory(uri: String, callback: (Result<Unit>) -> Unit) = submit(callback) {
        require(valid(uri)); db().deleteVisitsFor(uri)
    }
    fun clearHistory(callback: (Result<Unit>) -> Unit) = submit(callback) { db().deleteEverythingHistory() }
    fun bookmarks(callback: (Result<List<Bookmark>>) -> Unit) = submit(callback) {
        db().bookmarksGetRecent(100).mapNotNull { item ->
            (item as? BookmarkItem.Bookmark)?.b?.takeIf { valid(it.url) }?.let { Bookmark(it.guid, it.url, it.title.orEmpty().ifEmpty { it.url }) }
        }
    }
    fun saveBookmark(mode: BrowsingMode, uri: String, title: String, callback: (Result<String>) -> Unit) {
        if (mode == BrowsingMode.PRIVATE) { callback(Result.failure(IllegalStateException("Private bookmark writes are disabled"))); return }
        submit(callback) {
            require(valid(uri)); require(title.length <= 512)
            val db = db()
            val previous = db.bookmarksGetAllWithUrl(uri).filterIsInstance<BookmarkItem.Bookmark>().firstOrNull()?.b
            if (previous != null) {
                db.bookmarksUpdate(BookmarkUpdateInfo(previous.guid, title, null, null, null)); previous.guid
            } else db.bookmarksInsert(InsertableBookmarkItem.Bookmark(InsertableBookmark(
                parentGuid = "mobile______", position = BookmarkPosition.Append, url = uri, title = title)))
        }
    }
    fun editBookmark(id: String, uri: String, title: String, callback: (Result<Unit>) -> Unit) = submit(callback) {
        require(valid(uri)); require(title.length <= 512)
        require(db().bookmarksGetByGuid(id, false) is BookmarkItem.Bookmark)
        db().bookmarksUpdate(BookmarkUpdateInfo(id, title, uri, null, null))
    }
    fun deleteBookmark(id: String, callback: (Result<Boolean>) -> Unit) = submit(callback) {
        require(db().bookmarksGetByGuid(id, false) is BookmarkItem.Bookmark)
        db().bookmarksDelete(id)
    }
    internal fun close(callback: (Result<Unit>) -> Unit) = submit(callback) {
        connection?.close(); api?.close(); connection = null; api = null; closed = true
        io.shutdown()
    }
}
