/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

import java.net.URI
import java.net.URLEncoder

/** Explicit web-only boundary. External intents and privileged engine pages need separate UI. */
object NavigationPolicy {
    fun allows(uri: String): Boolean = try {
        val parsed = URI(uri)
        parsed.scheme?.lowercase() in setOf("http", "https") &&
            !parsed.host.isNullOrBlank() && parsed.rawUserInfo == null &&
            (parsed.port == -1 || parsed.port in 1..65535)
    } catch (_: Exception) { false }

    /** about:blank is inert, and is what Gecko requests for script-opened popups (OAuth, payments). */
    fun allowsOrBlank(uri: String): Boolean = uri == "about:blank" || allows(uri)

    // host:port with optional path/query/fragment. Digits after the colon distinguish it from a URI scheme.
    private val hostPort = Regex("^(?:\\[[0-9a-fA-F:.%]+\\]|[a-zA-Z0-9.-]+):[0-9]+(?:[/?#]\\S*)?$")

    fun address(input: String): String? {
        val text = input.trim()
        if (text.isEmpty()) return null
        if (allows(text)) return text
        if (hostPort.matches(text)) {
            val guessed = "https://$text"
            val parsed = runCatching { URI(guessed) }.getOrNull() ?: return null
            val host = parsed.host ?: return null
            val port = parsed.port
            return guessed.takeIf { port in 1..65535 && (host.contains('.') || host == "localhost" || host.startsWith("[")) && allows(it) }
        }
        // Never turn an explicit unsupported scheme into an engine load.
        if (Regex("^[a-zA-Z][a-zA-Z0-9+.-]*:").containsMatchIn(text)) return null
        val guessed = "https://$text"
        if (!text.any { it.isWhitespace() } && (text.contains('.') || text == "localhost") && allows(guessed)) {
            return guessed
        }
        return "https://duckduckgo.com/?q=" + URLEncoder.encode(text, "UTF-8")
    }
}
