/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

import java.net.URI
import java.net.URLEncoder

/** Explicit web-only boundary. External intents and privileged engine pages need separate UI. */
object NavigationPolicy {
    fun allows(uri: String): Boolean = try {
        val parsed = URI(uri)
        parsed.scheme?.lowercase() in setOf("http", "https") &&
            !parsed.host.isNullOrBlank() && parsed.rawUserInfo == null
    } catch (_: Exception) { false }

    fun address(input: String): String? {
        val text = input.trim()
        if (text.isEmpty()) return null
        if (allows(text)) return text
        // Never turn an explicit unsupported scheme into an engine load.
        if (Regex("^[a-zA-Z][a-zA-Z0-9+.-]*:").containsMatchIn(text)) return null
        val guessed = "https://$text"
        if (!text.any { it.isWhitespace() } && (text.contains('.') || text == "localhost") && allows(guessed)) {
            return guessed
        }
        return "https://duckduckgo.com/?q=" + URLEncoder.encode(text, "UTF-8")
    }
}
