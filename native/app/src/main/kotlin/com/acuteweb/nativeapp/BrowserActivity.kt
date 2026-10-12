/* SPDX-License-Identifier: MPL-2.0 */
package com.acuteweb.nativeapp

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.*
import com.acuteweb.core.NavigationPolicy
import com.acuteweb.core.PageState
import org.mozilla.geckoview.GeckoView

/** Native Android controls, independent of upstream Firefox UI. Prototype only. */
class BrowserActivity : Activity() {
    private lateinit var engine: GeckoBrowserEngine
    private lateinit var gecko: GeckoView
    private lateinit var address: EditText
    private lateinit var back: Button
    private lateinit var forward: Button
    private lateinit var status: TextView
    private var state = PageState()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(Color.rgb(17, 18, 20)) }
        // Window insets keep controls outside system bars on edge-to-edge Android.
        root.setOnApplyWindowInsetsListener { view, insets ->
            val bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() or android.view.WindowInsets.Type.ime())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom); insets
        }
        val bar = LinearLayout(this).apply {
            gravity = android.view.Gravity.CENTER_VERTICAL
            background = GradientDrawable().apply {
                cornerRadius = dp(28).toFloat(); setColor(Color.rgb(42, 44, 48)); setStroke(dp(1), Color.rgb(90, 92, 96))
            }
        }
        back = button("‹", "Back") { engine.back() }
        forward = button("›", "Forward") { engine.forward() }
        address = EditText(this).apply {
            setTextColor(Color.WHITE); hint = "Search or address"; setHintTextColor(Color.LTGRAY)
            setSingleLine(true); textSize = 16f
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
            imeOptions = EditorInfo.IME_ACTION_GO
            setOnEditorActionListener { _, action, event ->
                if (action == EditorInfo.IME_ACTION_GO || (event?.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)) {
                    navigate(); true
                } else false
            }
        }
        bar.addView(back); bar.addView(forward)
        bar.addView(address, LinearLayout.LayoutParams(0, dp(52), 1f))
        bar.addView(button("↻", "Reload") { engine.reload() })
        root.addView(bar, LinearLayout.LayoutParams(-1, -2).apply { setMargins(dp(8), dp(8), dp(8), dp(8)) })
        status = TextView(this).apply {
            text = "Native foundation preview · data migration and feature parity pending"
            setTextColor(Color.LTGRAY); setPadding(dp(12), 0, dp(12), dp(8)); textSize = 12f
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        root.addView(status)
        gecko = GeckoView(this)
        root.addView(gecko, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        engine = GeckoBrowserEngine((application as AcuteApplication).runtime, ::render)
        gecko.setSession(engine.session)
        render(state)
        // Preserve only a validated address for this first slice; session persistence is a release gate.
        val restored = savedInstanceState?.getString("uri")
        if (restored != null && NavigationPolicy.allows(restored)) engine.navigate(restored)
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun button(label: String, description: String, action: () -> Unit) = Button(this).apply {
        text = label; contentDescription = description; setTextColor(Color.WHITE)
        minWidth = 0; minimumWidth = 0; setPadding(0, 0, 0, 0)
        layoutParams = LinearLayout.LayoutParams(dp(48), dp(48)); setOnClickListener { action() }
    }
    private fun navigate() {
        val uri = NavigationPolicy.address(address.text.toString())
        if (uri == null) { status.text = "Enter a web address or search text"; return }
        address.clearFocus(); engine.navigate(uri)
        (getSystemService(INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager).hideSoftInputFromWindow(address.windowToken, 0)
    }
    private fun render(next: PageState) {
        state = next; back.isEnabled = next.canGoBack
        forward.visibility = if (next.canGoForward) View.VISIBLE else View.GONE
        if (!address.hasFocus()) address.setText(next.uri)
        status.text = next.error ?: "Native foundation preview · data migration and feature parity pending"
        title = next.title
    }
    override fun onSaveInstanceState(outState: Bundle) { outState.putString("uri", state.uri); super.onSaveInstanceState(outState) }
    override fun onStart() { super.onStart(); engine.session.setActive(true) }
    override fun onStop() { engine.session.setActive(false); super.onStop() }
    override fun onDestroy() { gecko.releaseSession(); engine.close(); super.onDestroy() }
    @Deprecated("Platform back compatibility")
    override fun onBackPressed() { if (state.canGoBack) engine.back() else super.onBackPressed() }
}
