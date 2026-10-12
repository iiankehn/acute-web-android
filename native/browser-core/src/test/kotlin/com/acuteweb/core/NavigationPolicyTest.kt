package com.acuteweb.core

import org.junit.Assert.*
import org.junit.Test

class NavigationPolicyTest {
    @Test fun webNavigation() {
        assertTrue(NavigationPolicy.allows("https://example.com/path?q=x#part"))
        assertTrue(NavigationPolicy.allows("http://example.com:8080/"))
        assertFalse(NavigationPolicy.allows("https://user:password@example.com/"))
        assertFalse(NavigationPolicy.allows("https:///missing-host"))
    }
    @Test fun rejectsPrivilegedAndExternalSchemes() {
        for (uri in listOf("javascript:alert(1)", "file:///etc/passwd", "content://data", "intent://example", "about:config", "data:text/html,test")) {
            assertFalse(uri, NavigationPolicy.allows(uri))
            assertNull(uri, NavigationPolicy.address(uri))
        }
    }
    @Test fun resolvesAddressesAndEncodesSearch() {
        assertEquals("https://example.com/path", NavigationPolicy.address(" example.com/path "))
        assertEquals("https://duckduckgo.com/?q=cats+%26+foxes", NavigationPolicy.address("cats & foxes"))
        assertNull(NavigationPolicy.address("  "))
    }
}
