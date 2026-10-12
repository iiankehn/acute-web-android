package com.acuteweb.core

import javax.crypto.KeyGenerator
import org.junit.Assert.*
import org.junit.Test

class SessionArchiveCodecTest {
    private val key = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
    private val codec = SessionArchiveCodec { key }
    private val saved = SavedTabs("one", listOf(SavedTab("one", "https://example.com/normal", "Normal", "form-state")))
    @Test fun authenticatedRoundTripPreservesOpaqueGeckoState() {
        val bytes = codec.encode(saved)
        assertEquals(saved, codec.decode(bytes))
        assertFalse(bytes.toString(Charsets.ISO_8859_1).contains("form-state"))
        assertFalse(bytes.toString(Charsets.ISO_8859_1).contains("example.com"))
        assertFalse(bytes.contentEquals(codec.encode(saved))) // Fresh GCM nonce for every write.
    }
    @Test fun tamperedAndTruncatedArchivesAreRejected() {
        val bytes = codec.encode(saved)
        for (bad in listOf(bytes.copyOf(15), bytes.copyOf().apply { this[lastIndex] = (this[lastIndex].toInt() xor 1).toByte() }, bytes.copyOf().apply { this[0] = 99 })) {
            try { codec.decode(bad); fail("Damaged archive accepted") } catch (_: Exception) { }
        }
    }
    @Test fun anotherKeyCannotReadSessionData() {
        val otherKey = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
        try { SessionArchiveCodec { otherKey }.decode(codec.encode(saved)); fail("Wrong key accepted") } catch (_: Exception) { }
    }
    @Test fun duplicateOrUnsafeTabsCannotBeWritten() {
        for (bad in listOf(SavedTabs(null, listOf(SavedTab("one", "content://secret", "", null))), SavedTabs(null, saved.tabs + saved.tabs))) {
            try { codec.encode(bad); fail("Invalid archive written") } catch (_: IllegalArgumentException) { }
        }
    }
}
