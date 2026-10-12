/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.core

import org.junit.Assert.*
import org.junit.Test

class LinkPolicyTest {
    @Test fun preservesFunctionalBytesOrderingAndFragment() {
        assertEquals("https://example.com/path?token=A%2Bb&mode=one+two&token=%2F#section?utm_source=keep",
            LinkPolicy.clean("https://example.com/path?token=A%2Bb&utm_source=ad&mode=one+two&fbclid=id&token=%2F#section?utm_source=keep"))
    }
    @Test fun understandsEncodedNamesAndUsesLocaleIndependentMatching() {
        assertEquals("https://example.com/", LinkPolicy.clean("https://example.com/?%75tm_SOURCE=ad&IGSHID=id"))
    }
    @Test fun offersNoActionWithoutRecognizedTrackingAndRejectsUnsafeUrls() {
        assertNull(LinkPolicy.clean("https://example.com/?id=1&campaign=keep"))
        assertNull(LinkPolicy.clean("javascript:alert(1)?utm_source=ad"))
        assertNull(LinkPolicy.clean("https://user:password@example.com/?gclid=id"))
    }
    @Test fun preservesEmptyQueryPartsAndExplicitEmptyFragment() {
        assertEquals("https://example.com/?&x=1&#", LinkPolicy.clean("https://example.com/?utm_source=ad&&x=1&#"))
    }
}
