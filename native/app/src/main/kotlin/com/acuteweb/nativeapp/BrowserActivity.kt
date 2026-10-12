/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.app.Activity
import android.app.AlertDialog
import android.os.Build
import android.os.Bundle
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.widget.*
import androidx.core.view.doOnPreDraw
import com.acuteweb.core.BrowsingMode
import org.mozilla.geckoview.GeckoSession
import org.mozilla.geckoview.GeckoView

/** Native controls attach to process-owned sessions; Android bundles never receive browsing data. */
class BrowserActivity : Activity() {
    private lateinit var documents: DocumentUi
    private lateinit var downloadUi: DownloadUi
    private lateinit var library: LibraryUi
    private lateinit var browser: BrowserController
    private lateinit var gecko: GeckoView
    private lateinit var geckoHost: FrameLayout
    private lateinit var address: EditText
    private lateinit var back: Button
    private lateinit var forward: Button
    private lateinit var tabCount: Button
    private lateinit var menu: Button
    private lateinit var status: TextView
    private lateinit var tabStrip: LinearLayout
    private lateinit var tabScroll: HorizontalScrollView
    private var pendingExternalUri: String? = null
    private var linkDialog: AlertDialog? = null
    private var linkTab: String? = null
    private var attachedSession: GeckoSession? = null
    private var renderedTab: String? = null
    private val observer: () -> Unit = { render() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        browser = (application as AcuteApplication).browser
        library = LibraryUi(this, browser, (application as AcuteApplication).places)
        downloadUi = DownloadUi(this, browser, (application as AcuteApplication).downloads)
        documents = DocumentUi(this, browser, (application as AcuteApplication).downloads)
        applyPrivacy()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setBackgroundColor(Color.rgb(17, 18, 20))
            isSaveEnabled = false; isSaveFromParentEnabled = false
        }
        root.setOnApplyWindowInsetsListener { view, insets ->
            val bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() or android.view.WindowInsets.Type.ime())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom); insets
        }
        tabStrip = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        tabScroll = HorizontalScrollView(this).apply { addView(tabStrip); isHorizontalScrollBarEnabled = false }
        root.addView(tabScroll, LinearLayout.LayoutParams(-1, -2))
        val bar = LinearLayout(this).apply { gravity = android.view.Gravity.CENTER_VERTICAL; background = capsule(false) }
        back = button("‹", getString(R.string.back)) { browser.selectedEngine()?.back() }
        forward = button("›", getString(R.string.forward)) { browser.selectedEngine()?.forward() }
        address = EditText(this).apply {
            isSaveEnabled = false; isSaveFromParentEnabled = false
            setTextColor(Color.WHITE); hint = getString(R.string.address_hint); setHintTextColor(Color.LTGRAY)
            setSingleLine(true); textSize = 16f
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
            imeOptions = EditorInfo.IME_ACTION_GO
            setOnEditorActionListener { _, action, event ->
                if (action == EditorInfo.IME_ACTION_GO || (event?.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)) {
                    navigate(); true
                } else false
            }
        }
        tabCount = button("1", getString(R.string.tabs_section)) { showTabs() }
        menu = button("⋮", getString(R.string.menu)) { showMenu() }
        bar.addView(back); bar.addView(forward)
        bar.addView(address, LinearLayout.LayoutParams(0, dp(52), 1f))
        bar.addView(tabCount); bar.addView(menu)
        root.addView(bar, LinearLayout.LayoutParams(-1, -2).apply { setMargins(dp(8), dp(8), dp(8), dp(8)) })
        status = TextView(this).apply {
            setTextColor(Color.LTGRAY); setPadding(dp(12), 0, dp(12), dp(8)); textSize = 12f
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        root.addView(status)
        gecko = newGeckoView()
        geckoHost = FrameLayout(this).apply { addView(gecko, FrameLayout.LayoutParams(-1, -1)) }
        root.addView(geckoHost, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addOnLayoutChangeListener { _, left, _, right, _, oldLeft, _, oldRight, _ ->
            if (right - left != oldRight - oldLeft) {
                tabScroll.visibility = if (right - left >= dp(600)) View.VISIBLE else View.GONE
            }
        }
        tabScroll.visibility = if (resources.configuration.screenWidthDp >= 600) View.VISIBLE else View.GONE
        setContentView(root)
        if (Build.VERSION.SDK_INT >= 33) {
            onBackInvokedDispatcher.registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT) { handleBack() }
        }
        receiveExternal(intent)
        render()
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun capsule(selected: Boolean) = GradientDrawable().apply {
        cornerRadius = dp(28).toFloat()
        setColor(if (selected) Color.rgb(64, 66, 72) else Color.rgb(42, 44, 48))
        setStroke(dp(1), if (selected) Color.LTGRAY else Color.rgb(90, 92, 96))
    }
    private fun button(label: String, description: String, action: () -> Unit) = Button(this).apply {
        text = label; contentDescription = description; setTextColor(Color.WHITE)
        minWidth = 0; minimumWidth = 0; setPadding(0, 0, 0, 0)
        layoutParams = LinearLayout.LayoutParams(dp(48), dp(48)); setOnClickListener { action() }
    }
    private fun navigate() {
        if (!browser.navigate(address.text.toString())) { status.setText(R.string.invalid_address); return }
        address.clearFocus()
        (getSystemService(INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager).hideSoftInputFromWindow(address.windowToken, 0)
    }
    private fun applyPrivacy() {
        if (browser.tabs.mode == BrowsingMode.PRIVATE) window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
    }
    private fun newGeckoView() = GeckoView(this).apply { isSaveEnabled = false; isSaveFromParentEnabled = false }
    private fun render() {
        if (!::gecko.isInitialized) return
        if (browser.ready) pendingExternalUri?.let { uri ->
            pendingExternalUri = null
            intent?.data = null // Consumed once; rotation must not open the same link again.
            // External Android links always enter a fresh normal tab, never the live private window.
            if (browser.newTab(BrowsingMode.NORMAL)) browser.navigate(uri)
            else Toast.makeText(this, R.string.tab_limit, Toast.LENGTH_SHORT).show()
        }
        applyPrivacy()
        downloadUi.refresh()
        documents.refresh()
        if (browser.tabs.mode == BrowsingMode.PRIVATE) library.dismiss()
        val tab = browser.tabs.selected
        if (linkTab != tab?.id) { linkDialog?.dismiss(); linkDialog = null; linkTab = null }
        val engine = if (browser.ready) browser.selectedEngine() else null
        if (engine?.session !== attachedSession) {
            if (attachedSession != null) gecko.releaseSession()
            // Discard the previous surface and autofill hierarchy at every tab/privacy boundary.
            geckoHost.removeAllViews()
            gecko = newGeckoView()
            geckoHost.addView(gecko, FrameLayout.LayoutParams(-1, -1))
            attachedSession = engine?.session
            if (engine != null) gecko.setSession(engine.session)
        }
        if (renderedTab != tab?.id || !address.hasFocus()) {
            address.setText(tab?.page?.uri.orEmpty())
            if (renderedTab != tab?.id) address.clearFocus()
        }
        renderedTab = tab?.id
        address.isEnabled = browser.ready; menu.isEnabled = browser.ready; tabCount.isEnabled = browser.ready
        back.isEnabled = tab?.page?.canGoBack == true
        forward.visibility = if (tab?.page?.canGoForward == true) View.VISIBLE else View.GONE
        tabCount.text = getString(R.string.tab_count, browser.tabs.visible.size)
        tabCount.contentDescription = getString(R.string.open_tabs, browser.tabs.visible.size)
        val private = browser.tabs.mode == BrowsingMode.PRIVATE
        status.text = if (!browser.ready) getString(R.string.restoring_tabs)
            else tab?.page?.error ?: (if (private) getString(R.string.private_hint) else browser.storageError ?: (if ((application as AcuteApplication).places.hasError) getString(R.string.library_error) else getString(R.string.normal_hint)))
        title = if (private) getString(R.string.private_title) else getString(R.string.app_name)
        if (!private) geckoHost.doOnPreDraw { host -> host.post {
            // Keep protection until the private surface has been removed and the normal frame drawn.
            if (browser.tabs.mode == BrowsingMode.NORMAL && !isFinishing) window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
        } }
        tabStrip.removeAllViews()
        browser.tabs.visible.forEach { item ->
            val label = item.page.title.takeIf { item.page.uri.isNotEmpty() } ?: getString(R.string.new_tab)
            val tabButton = Button(this).apply {
                text = label; setTextColor(Color.WHITE); background = capsule(item.id == tab?.id)
                isSelected = item.id == tab?.id; setSingleLine(true); ellipsize = android.text.TextUtils.TruncateAt.END
                setOnClickListener { browser.select(item.id) }
                setOnLongClickListener { browser.close(item.id); true }
                contentDescription = label
            }
            tabStrip.addView(tabButton, LinearLayout.LayoutParams(dp(180), dp(48)).apply { setMargins(dp(4), dp(8), dp(4), 0) })
        }
    }
    private fun addTab(mode: BrowsingMode = browser.tabs.mode) {
        if (!browser.newTab(mode)) Toast.makeText(this, R.string.tab_limit, Toast.LENGTH_SHORT).show()
    }
    private fun showMenu() {
        val private = browser.tabs.mode == BrowsingMode.PRIVATE
        PopupMenu(this, menu).apply {
            menu.add(R.string.tabs_section).isEnabled = false
            menu.add(R.string.new_tab).setOnMenuItemClickListener { addTab(); true }
            menu.add(R.string.new_private_tab).setOnMenuItemClickListener { addTab(BrowsingMode.PRIVATE); true }
            menu.add(if (private) R.string.normal_tabs else R.string.private_tabs).setOnMenuItemClickListener {
                browser.switchMode(if (private) BrowsingMode.NORMAL else BrowsingMode.PRIVATE); true
            }
            menu.add(R.string.close_tab).setOnMenuItemClickListener { browser.tabs.selected?.let { browser.close(it.id) }; true }
            menu.add(R.string.page_section).isEnabled = false
            menu.add(R.string.reload).setOnMenuItemClickListener { browser.selectedEngine()?.reload(); true }
            menu.add(R.string.downloads_session).setOnMenuItemClickListener { downloadUi.show(); true }
            menu.add(R.string.save_pdf).setOnMenuItemClickListener { documents.export(); true }
            if (documents.printAvailable) menu.add(R.string.print_page).setOnMenuItemClickListener { documents.export(true); true }
            menu.add(R.string.edit_address).setOnMenuItemClickListener { focusAddress(); true }
            if (!private) {
                menu.add(R.string.library_section).isEnabled = false
                menu.add(R.string.save_bookmark).setOnMenuItemClickListener { library.bookmarkPage(); true }
                menu.add(R.string.recent_bookmarks).setOnMenuItemClickListener { library.bookmarks(); true }
                menu.add(R.string.recent_history).setOnMenuItemClickListener { library.history(); true }
            }
            if (private) {
                menu.add(R.string.privacy_section).isEnabled = false
                menu.add(R.string.close_private_tabs).setOnMenuItemClickListener { browser.closePrivateTabs(); true }
            }
            show()
        }
    }
    private fun showTabs() {
        val private = browser.tabs.mode == BrowsingMode.PRIVATE
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val dialog = AlertDialog.Builder(this).setTitle(if (private) R.string.private_tabs else R.string.normal_tabs)
            .setView(ScrollView(this).apply { addView(list) })
            .setPositiveButton(R.string.new_tab) { _, _ -> addTab() }
            .setNeutralButton(if (private) R.string.normal_tabs else R.string.private_tabs) { _, _ ->
                browser.switchMode(if (private) BrowsingMode.NORMAL else BrowsingMode.PRIVATE)
            }.create()
        if (private) dialog.window?.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        browser.tabs.visible.forEach { tab ->
            val row = LinearLayout(this)
            row.addView(Button(this).apply {
                text = tab.page.title.takeIf { tab.page.uri.isNotEmpty() } ?: getString(R.string.new_tab)
                isSelected = tab.id == browser.tabs.selected?.id
                setOnClickListener { dialog.dismiss(); browser.select(tab.id) }
            }, LinearLayout.LayoutParams(0, -2, 1f))
            row.addView(button("×", getString(R.string.close_tab)) { dialog.dismiss(); browser.close(tab.id) })
            list.addView(row)
        }
        dialog.show()
    }
    private fun showLinkActions(tabId: String, uri: String) {
        if (browser.tabs.selected?.id != tabId || isFinishing) return
        linkDialog?.dismiss(); linkTab = tabId
        val private = browser.tabs.mode == BrowsingMode.PRIVATE
        val clean = com.acuteweb.core.LinkPolicy.clean(uri)
        val labels = mutableListOf(getString(R.string.open_link_tab), getString(R.string.copy_link), getString(R.string.share_link))
        if (clean != null) labels.add(getString(R.string.copy_clean_link))
        val dialog = AlertDialog.Builder(this).setTitle(uri).setItems(labels.toTypedArray()) { _, action ->
            if (browser.tabs.selected?.id != tabId || browser.tabs.mode != (if (private) BrowsingMode.PRIVATE else BrowsingMode.NORMAL)) return@setItems
            when (action) {
                0 -> if (browser.newTab()) browser.navigate(uri) else Toast.makeText(this, R.string.tab_limit, Toast.LENGTH_SHORT).show()
                1, 3 -> {
                    val clip = android.content.ClipData.newPlainText(getString(R.string.link_label), if (action == 3) clean ?: uri else uri)
                    if (private && Build.VERSION.SDK_INT >= 33) clip.description.extras = android.os.PersistableBundle().apply {
                        putBoolean(android.content.ClipDescription.EXTRA_IS_SENSITIVE, true)
                    }
                    (getSystemService(CLIPBOARD_SERVICE) as android.content.ClipboardManager).setPrimaryClip(clip)
                    Toast.makeText(this, R.string.link_copied, Toast.LENGTH_SHORT).show()
                }
                2 -> {
                    val intent = android.content.Intent(android.content.Intent.ACTION_SEND).apply {
                        type = "text/plain"; putExtra(android.content.Intent.EXTRA_TEXT, uri)
                    }
                    runCatching { startActivity(android.content.Intent.createChooser(intent, getString(R.string.share_link))) }
                        .onFailure { Toast.makeText(this, R.string.share_unavailable, Toast.LENGTH_SHORT).show() }
                }
            }
        }.create()
        if (private) dialog.window?.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        linkDialog = dialog; dialog.show()
    }
    private fun receiveExternal(incoming: android.content.Intent?) {
        if (incoming?.action != android.content.Intent.ACTION_VIEW) return
        val uri = incoming.dataString ?: return
        if (uri.length <= 4096 && com.acuteweb.core.NavigationPolicy.allows(uri)) pendingExternalUri = uri
    }
    override fun onNewIntent(incoming: android.content.Intent) {
        super.onNewIntent(incoming); setIntent(incoming); receiveExternal(incoming); render()
    }
    @Deprecated("Platform file picker callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == DownloadUi.CREATE_DOWNLOAD) downloadUi.result(resultCode, data)
    }
    private fun focusAddress() {
        address.requestFocus(); address.selectAll()
        (getSystemService(INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager).showSoftInput(address, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)
    }
    override fun onStart() { super.onStart(); downloadUi.start(); browser.linkHandler = ::showLinkActions; (application as AcuteApplication).places.attach(observer); browser.attach(observer) }
    override fun onStop() { documents.stop(); downloadUi.stop(); library.dismiss(); linkDialog?.dismiss(); linkDialog = null; browser.linkHandler = null; (application as AcuteApplication).places.detach(observer); browser.detach(observer); super.onStop() }
    override fun onDestroy() {
        documents.destroy()
        if (attachedSession != null) gecko.releaseSession()
        attachedSession = null
        if (isFinishing && !isChangingConfigurations) { downloadUi.finish(); browser.closePrivateTabs() }
        super.onDestroy()
    }
    // Framework hierarchy saving is disabled on every browser view; no private URL/state enters this bundle.
    override fun onSaveInstanceState(outState: Bundle) { super.onSaveInstanceState(outState) }
    private fun handleBack() {
        val tab = browser.tabs.selected
        if (tab?.page?.canGoBack == true) browser.selectedEngine()?.back() else finish()
    }
    @Deprecated("Legacy Android 12 back handling")
    override fun onBackPressed() { handleBack() }
    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (event.isCtrlPressed && browser.ready) {
            when (keyCode) {
                KeyEvent.KEYCODE_L -> focusAddress()
                KeyEvent.KEYCODE_T -> addTab()
                KeyEvent.KEYCODE_W -> browser.tabs.selected?.let { browser.close(it.id) }
                KeyEvent.KEYCODE_P -> if (event.isShiftPressed) browser.switchMode(if (browser.tabs.mode == BrowsingMode.PRIVATE) BrowsingMode.NORMAL else BrowsingMode.PRIVATE) else return super.onKeyDown(keyCode, event)
                KeyEvent.KEYCODE_TAB -> {
                    val tabs = browser.tabs.visible
                    if (tabs.isNotEmpty()) {
                        val current = tabs.indexOfFirst { it.id == browser.tabs.selected?.id }
                        val offset = if (event.isShiftPressed) -1 else 1
                        browser.select(tabs[(current + offset + tabs.size) % tabs.size].id)
                    }
                }
                else -> return super.onKeyDown(keyCode, event)
            }
            return true
        }
        return super.onKeyDown(keyCode, event)
    }
}
