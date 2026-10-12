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
    @Test fun resolvesHostAndPort() {
        assertEquals("https://example.com:8080", NavigationPolicy.address("example.com:8080"))
        assertEquals("https://example.com:8443/a?b=c#d", NavigationPolicy.address("example.com:8443/a?b=c#d"))
        assertEquals("https://localhost:3000", NavigationPolicy.address("localhost:3000"))
        assertEquals("https://192.168.1.1:8080", NavigationPolicy.address("192.168.1.1:8080"))
        assertNull(NavigationPolicy.address("example.com:99999"))
        assertNull(NavigationPolicy.address("example.com:0"))
        assertNull(NavigationPolicy.address("myserver:8080"))
        assertNull(NavigationPolicy.address("mailto:123"))
    }
    @Test fun blankIsOnlyAllowedForWindowsAndLoads() {
        assertTrue(NavigationPolicy.allowsOrBlank("about:blank"))
        assertTrue(NavigationPolicy.allowsOrBlank("https://example.com/"))
        assertFalse(NavigationPolicy.allows("about:blank"))
        assertFalse(NavigationPolicy.allowsOrBlank("about:config"))
        assertFalse(NavigationPolicy.allowsOrBlank("about:blank#x"))
        assertNull(NavigationPolicy.address("about:blank"))
    }
    @Test fun rejectsInvalidPortsAcrossAllEntryPaths() {
        for (input in listOf("example.com:100000", "192.168.1.1:100000", "localhost:999999999999999999", "https://example.com:99999", "https://example.com:0")) {
            assertNull(input, NavigationPolicy.address(input))
            assertFalse(input, NavigationPolicy.allows(input))
        }
        assertEquals("https://[::1]:8443/a", NavigationPolicy.address("[::1]:8443/a"))
        assertTrue(NavigationPolicy.allows("https://example.com:65535"))
    }

}
