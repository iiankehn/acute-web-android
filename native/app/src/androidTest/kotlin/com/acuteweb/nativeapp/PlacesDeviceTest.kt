/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import androidx.test.ext.junit.runners.AndroidJUnit4
import com.acuteweb.core.BrowsingMode
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

internal fun <T> storageResult(operation: ((Result<T>) -> Unit) -> Unit): Result<T> {
    val latch = CountDownLatch(1)
    val value = AtomicReference<Result<T>>()
    onMain { operation { value.set(it); latch.countDown() } }
    assertTrue("Timed out waiting for Places", latch.await(20, TimeUnit.SECONDS))
    return value.get()
}
internal fun <T> storage(operation: ((Result<T>) -> Unit) -> Unit): T = storageResult(operation).getOrThrow()

@RunWith(AndroidJUnit4::class)
class PlacesDeviceTest {
    @Test fun bookmarkCrudKeepsIdsAndMetadataAcrossDatabaseReopen() {
        val name = "bookmarks-${UUID.randomUUID()}.sqlite"
        var places = PlacesStore(app, name)
        val uri = "https://example.com/bookmark-${UUID.randomUUID()}"
        try {
            val id = storage<String> { places.saveBookmark(BrowsingMode.NORMAL, uri, "Original", it) }
            val same = storage<String> { places.saveBookmark(BrowsingMode.NORMAL, uri, "Updated", it) }
            assertEquals(id, same)
            assertEquals(1, storage<List<PlacesStore.Bookmark>> { places.bookmarks(it) }.size)
            storage<Unit> { places.close(it) }
            places = PlacesStore(app, name)
            assertEquals(PlacesStore.Bookmark(id, uri, "Updated"), storage<List<PlacesStore.Bookmark>> { places.bookmarks(it) }.single())
            storage<Unit> { places.editBookmark(id, uri + "/edited", "Edited", it) }
            assertEquals(uri + "/edited", storage<List<PlacesStore.Bookmark>> { places.bookmarks(it) }.single().uri)
            assertTrue(storage<Boolean> { places.deleteBookmark(id, it) })
            assertTrue(storage<List<PlacesStore.Bookmark>> { places.bookmarks(it) }.isEmpty())
        } finally { storage<Unit> { places.close(it) } }
    }
    @Test fun historyRejectsPrivateWritesAndQueriesAndClearPreservesBookmarks() {
        val places = PlacesStore(app, "history-${UUID.randomUUID()}.sqlite")
        val normal = "https://example.com/normal-${UUID.randomUUID()}"
        val private = "https://example.com/private-secret-${UUID.randomUUID()}"
        try {
            storage<String> { places.saveBookmark(BrowsingMode.NORMAL, normal, "Keep", it) }
            assertTrue(storage<Boolean> { places.recordVisit(BrowsingMode.NORMAL, normal, callback = it) })
            assertFalse(storage<Boolean> { places.recordVisit(BrowsingMode.PRIVATE, private, callback = it) })
            onMain { places.updateTitle(BrowsingMode.PRIVATE, normal, "Private secret") }
            assertTrue(storageResult<String> { places.saveBookmark(BrowsingMode.PRIVATE, private, "Secret", it) }.isFailure)
            assertArrayEquals(booleanArrayOf(true, false), storage<BooleanArray> { places.visited(BrowsingMode.NORMAL, listOf(normal, private), it) })
            assertArrayEquals(booleanArrayOf(false, false), storage<BooleanArray> { places.visited(BrowsingMode.PRIVATE, listOf(normal, private), it) })
            assertEquals(listOf(normal), storage<List<PlacesStore.Visit>> { places.history(it) }.map { it.uri })
            storage<Unit> { places.clearHistory(it) }
            assertTrue(storage<List<PlacesStore.Visit>> { places.history(it) }.isEmpty())
            assertEquals("Keep", storage<List<PlacesStore.Bookmark>> { places.bookmarks(it) }.single().title)
        } finally { storage<Unit> { places.close(it) } }
    }
    @Test fun unreadablePlacesDatabaseIsPreservedAndCannotBeOverwritten() {
        val name = "corrupt-${UUID.randomUUID()}.sqlite"
        val file = File(app.noBackupFilesDir, name)
        val damaged = ByteArray(4096) { 0x6a.toByte() }; file.writeBytes(damaged)
        val places = PlacesStore(app, name)
        try {
            assertTrue(storageResult<List<PlacesStore.Bookmark>> { places.bookmarks(it) }.isFailure)
            assertTrue(storageResult<String> { places.saveBookmark(BrowsingMode.NORMAL, "https://example.com", "No overwrite", it) }.isFailure)
            assertArrayEquals(damaged, file.readBytes())
        } finally { storage<Unit> { places.close(it) } }
    }
    @Test fun corruptTreeWithValidSqliteHeaderCannotBeSilentlyReset() {
        val name = "corrupt-tree-${UUID.randomUUID()}.sqlite"
        var places = PlacesStore(app, name)
        storage<String> { places.saveBookmark(BrowsingMode.NORMAL, "https://example.com/keep", "Keep", it) }
        storage<Unit> { places.close(it) }
        val file = File(app.noBackupFilesDir, name)
        val damaged = file.readBytes()
        assertTrue(damaged.size > 100)
        damaged[100] = 0 // Invalid first b-tree page type; the SQLite magic header stays intact.
        file.writeBytes(damaged)
        places = PlacesStore(app, name)
        try {
            assertTrue(storageResult<List<PlacesStore.Bookmark>> { places.bookmarks(it) }.isFailure)
            assertArrayEquals(damaged, file.readBytes())
        } finally { storage<Unit> { places.close(it) } }
    }
    @Test fun actualGeckoVisitsPersistOnlyNormalPages() {
        val places = PlacesStore(app, "gecko-history-${UUID.randomUUID()}.sqlite")
        try {
            TestSite().use { site ->
                SessionDriver(history = places).use { normal ->
                    normal.open(); val token = UUID.randomUUID().toString()
                    val uri = site.uri("/normal-history", token)
                    normal.load(uri, token)
                    eventually { storage<List<PlacesStore.Visit>> { places.history(it) }.any { it.uri == uri } }
                }
                SessionDriver(true, UUID.randomUUID().toString(), history = places).use { private ->
                    private.open(); val token = UUID.randomUUID().toString()
                    private.load(site.uri("/private-secret-history", token), token)
                    // The serial executor barrier follows all main-thread history callbacks.
                    assertFalse(storage<List<PlacesStore.Visit>> { places.history(it) }.any { it.uri.contains("private-secret") })
                }
            }
        } finally { storage<Unit> { places.close(it) } }
    }
}
