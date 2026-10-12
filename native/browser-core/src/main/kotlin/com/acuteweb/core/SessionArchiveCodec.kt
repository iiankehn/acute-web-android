/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Standard Kotlin JSON and JCE authenticated encryption; Android supplies the Keystore key. */
class SessionArchiveCodec(private val key: () -> SecretKey) {
    companion object { const val MAX_BYTES = 12 * 1024 * 1024; private const val VERSION: Byte = 1 }
    private val json = Json { ignoreUnknownKeys = false }
    private val aad = "acute-dev-normal-tabs-v1".toByteArray(Charsets.UTF_8)
    fun encode(snapshot: SavedTabs): ByteArray {
        Tabs().restore(snapshot) // Validate before touching the last good archive.
        val clear = json.encodeToString(snapshot).toByteArray(Charsets.UTF_8)
        require(clear.size <= MAX_BYTES - 64)
        try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.ENCRYPT_MODE, key()); cipher.updateAAD(aad)
            require(cipher.iv.size == 12)
            return byteArrayOf(VERSION) + cipher.iv + cipher.doFinal(clear)
        } finally { clear.fill(0) }
    }
    fun decode(bytes: ByteArray): SavedTabs {
        require(bytes.size in 30..MAX_BYTES && bytes[0] == VERSION)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(1, 13)))
        cipher.updateAAD(aad)
        val clear = cipher.doFinal(bytes, 13, bytes.size - 13)
        try {
            return json.decodeFromString<SavedTabs>(clear.toString(Charsets.UTF_8)).also { Tabs().restore(it) }
        } finally { clear.fill(0) }
    }
}
