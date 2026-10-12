package com.acuteweb.core

import org.junit.Assert.*
import org.junit.Test

class TabsTest {
    @Test fun privateTitlesAddressesAndEngineStateNeverEnterPersistence() {
        val tabs = Tabs(); val normal = tabs.add()!!
        tabs.update(normal.id, PageState(uri = "https://example.com/normal", title = "Normal"))
        tabs.saveEngineState(normal.id, "normal-gecko-state")
        val private = tabs.add(BrowsingMode.PRIVATE)!!
        tabs.update(private.id, PageState(uri = "https://example.com/secret", title = "Secret"))
        tabs.saveEngineState(private.id, "secret-form-data")
        val saved = tabs.normalSnapshot()
        assertEquals(listOf(normal.id), saved.tabs.map { it.id })
        assertEquals(normal.id, saved.selectedId)
        assertFalse(saved.toString().contains("secret"))
        val restarted = Tabs(); restarted.restore(saved)
        assertEquals(BrowsingMode.NORMAL, restarted.mode)
        assertEquals("normal-gecko-state", restarted.selected!!.engineState)
    }
    @Test fun modeSwitchKeepsIndependentSelections() {
        val tabs = Tabs(); val normal = tabs.add()!!; val private = tabs.add(BrowsingMode.PRIVATE)!!
        tabs.switchMode(BrowsingMode.NORMAL); assertEquals(normal.id, tabs.selected!!.id)
        tabs.switchMode(BrowsingMode.PRIVATE); assertEquals(private.id, tabs.selected!!.id)
    }
    @Test fun closingSelectedTabChoosesSurvivingTabOnlyInItsMode() {
        val tabs = Tabs(); val first = tabs.add()!!; val second = tabs.add()!!
        tabs.add(BrowsingMode.PRIVATE); tabs.select(second.id); tabs.close(second.id)
        assertEquals(first.id, tabs.selected!!.id)
        tabs.close(first.id); assertNull(tabs.selected)
        assertEquals(1, tabs.all.size)
    }
    @Test fun tabLimitsBoundResourceCreation() {
        val tabs = Tabs(); repeat(Tabs.MAX_NORMAL) { assertNotNull(tabs.add(BrowsingMode.NORMAL)) }
        assertNull(tabs.add(BrowsingMode.NORMAL))
        repeat(Tabs.MAX_PRIVATE) { assertNotNull(tabs.add(BrowsingMode.PRIVATE)) }
        assertNull(tabs.add(BrowsingMode.PRIVATE))
    }
    @Test fun newLocationCannotRestoreThePreviousDocument() {
        val tabs = Tabs(); val tab = tabs.add()!!
        tabs.update(tab.id, PageState(uri = "https://example.com/a")); tabs.saveEngineState(tab.id, "old-state")
        tabs.update(tab.id, PageState(uri = "https://example.com/b"))
        assertNull(tabs.selected!!.engineState)
    }
    @Test fun invalidRestoreDoesNotDestroyCurrentTabs() {
        val tabs = Tabs(); val original = tabs.add()!!
        for (saved in listOf(
            SavedTabs(null, listOf(SavedTab("id", "file:///secret", "", null))),
            SavedTabs(null, listOf(SavedTab("id", "", "", null), SavedTab("id", "", "", null))),
            SavedTabs(null, listOf(SavedTab("../bad", "", "", null))),
            SavedTabs(null, listOf(SavedTab("id", "", "", "x".repeat(Tabs.MAX_ENGINE_STATE + 1))))
        )) {
            try { tabs.restore(saved); fail("Invalid snapshot accepted") } catch (_: IllegalArgumentException) { }
            assertEquals(original.id, tabs.selected!!.id)
        }
    }
    @Test fun absentSelectionFallsBackAndClosedTabsDoNotReappear() {
        val tabs = Tabs(); val tab = tabs.add()!!; tabs.close(tab.id)
        val restored = Tabs(); restored.restore(tabs.normalSnapshot()); assertTrue(restored.all.isEmpty())
        restored.restore(SavedTabs("missing", listOf(SavedTab("known", "", "New tab", null))))
        assertEquals("known", restored.selected!!.id)
    }
}
