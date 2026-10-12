/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

import java.net.URLDecoder
import java.util.Locale

/** Extracted from the preserved Acute context action; retained URL bytes are never re-encoded. */
object LinkPolicy {
    private val tracking = setOf("dclid", "fbclid", "gbraid", "gclid", "igshid", "mc_cid", "mc_eid",
        "mkt_tok", "msclkid", "oly_anon_id", "oly_enc_id", "srsltid", "ttclid", "twclid", "vero_id",
        "wbraid", "_hsenc", "_hsmi")
    fun clean(raw: String): String? {
        if (raw.length > 4096 || !NavigationPolicy.allows(raw)) return null
        val address = raw.substringBefore('#')
        val fragment = if ('#' in raw) "#" + raw.substringAfter('#') else ""
        val query = address.indexOf('?').takeIf { it >= 0 } ?: return null
        val parts = address.substring(query + 1).split('&')
        val retained = parts.filterNot {
            val encoded = it.substringBefore('=')
            val name = runCatching { URLDecoder.decode(encoded, "UTF-8") }.getOrDefault(encoded).lowercase(Locale.ROOT)
            name.startsWith("utm_") || name in tracking
        }
        if (parts.size == retained.size) return null
        return address.substring(0, query) + (if (retained.isEmpty()) "" else "?" + retained.joinToString("&")) + fragment
    }
}
