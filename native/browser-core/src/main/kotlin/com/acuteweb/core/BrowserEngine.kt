/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

/** App-facing commands. Gecko types stay out of product logic. Main-thread confined. */
interface BrowserEngine {
    fun navigate(uri: String)
    fun back()
    fun forward()
    fun reload()
    fun close()
}

data class PageState(
    val uri: String = "",
    val title: String = "Acute",
    val canGoBack: Boolean = false,
    val canGoForward: Boolean = false,
    val error: String? = null,
)
