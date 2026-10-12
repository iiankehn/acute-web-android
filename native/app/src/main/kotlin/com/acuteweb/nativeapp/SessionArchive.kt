/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import com.acuteweb.core.SavedTabs
import com.acuteweb.core.SessionArchiveCodec
import java.io.File
import java.io.FileNotFoundException
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/** Called only on the persistence executor. Atomic replacement preserves the prior file on failure. */
class SessionArchive(context: Context, name: String = "normal-tabs-v1.enc") {
    init { require(name.matches(Regex("[a-zA-Z0-9-]+\\.enc"))) }
    private val file = AtomicFile(File(context.noBackupFilesDir, name))
    private val codec = SessionArchiveCodec(::getKey)
    private fun getKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val alias = "acute-dev-normal-tabs-v1"
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).build())
        }.generateKey()
    }
    fun read(): SavedTabs {
        val input = try { file.openRead() } catch (_: FileNotFoundException) {
            // Distinguish a new install from a present but unreadable archive.
            if (file.baseFile.exists() || File(file.baseFile.path + ".bak").exists() || File(file.baseFile.path + ".new").exists()) throw IllegalStateException("Archive unavailable")
            return SavedTabs(null, emptyList())
        }
        val bytes = input.use {
            require(file.baseFile.length() <= SessionArchiveCodec.MAX_BYTES)
            val output = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            while (true) {
                val count = it.read(buffer)
                if (count < 0) break
                require(output.size() + count <= SessionArchiveCodec.MAX_BYTES)
                output.write(buffer, 0, count)
            }
            output.toByteArray()
        }
        require(bytes.size <= SessionArchiveCodec.MAX_BYTES)
        return codec.decode(bytes)
    }
    fun write(snapshot: SavedTabs) {
        val bytes = codec.encode(snapshot)
        val output = file.startWrite()
        try {
            output.write(bytes); file.finishWrite(output)
            // AtomicFile logs a failed rename rather than throwing; do not report a failed commit as recovery.
            check(file.baseFile.isFile && !File(file.baseFile.path + ".new").exists()) { "Archive replacement failed" }
        }
        catch (error: Exception) { file.failWrite(output); throw error }
    }
}
