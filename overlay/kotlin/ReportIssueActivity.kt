package org.mozilla.fenix.acute

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.text.InputFilter
import android.view.WindowManager
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.mozilla.fenix.R

/** A local review screen; no issue URL exists until the tester approves the text. */
class ReportIssueActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        val crash = LocalCrashReports.read(this)
        val padding = (20 * resources.displayMetrics.density).toInt()
        val form = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }
        form.addView(TextView(this).apply { setText(R.string.acute_report_review_notice) })
        val include = CheckBox(this).apply {
            setText(R.string.acute_include_last_crash)
            isEnabled = crash != null
            isChecked = false
        }
        form.addView(include)
        if (crash == null) form.addView(TextView(this).apply { setText(R.string.acute_no_local_crash) })
        val options = AlertDialog.Builder(this)
            .setTitle(R.string.acute_report_issue_title)
            .setView(form)
            .setPositiveButton(R.string.acute_review_draft) { _, _ -> review(if (include.isChecked) crash else null) }
            .setNeutralButton(R.string.acute_delete_crash) { _, _ -> LocalCrashReports.delete(this); finish() }
            .setNegativeButton(android.R.string.cancel) { _, _ -> finish() }
            .setOnCancelListener { finish() }
            .show()
        options.window?.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
    }

    private fun review(crash: String?) {
        val draft = EditText(this).apply {
            filters = arrayOf(InputFilter.LengthFilter(5000))
            setText(getString(R.string.acute_issue_template) + if (crash != null) "\n\n```text\n$crash```\n" else "")
            imeOptions = android.view.inputmethod.EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING
            minLines = 10
            setSelectAllOnFocus(false)
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
        }
        val scroll = ScrollView(this).apply { addView(draft) }
        val dialog = AlertDialog.Builder(this)
            .setTitle(R.string.acute_review_draft)
            .setMessage(R.string.acute_issue_public_warning)
            .setView(scroll)
            .setPositiveButton(R.string.acute_open_github_draft, null)
            .setNegativeButton(android.R.string.cancel) { _, _ -> finish() }
            .setOnCancelListener { finish() }
            .show()
        dialog.window?.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            val url = Uri.Builder().scheme("https").authority("github.com")
                .path("iiankehn/acute-web-android/issues/new")
                .appendQueryParameter("title", "Android issue")
                .appendQueryParameter("body", draft.text.toString()).build()
            if (url.toString().length > 8000) {
                Toast.makeText(this, R.string.acute_issue_too_long, Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            try {
                startActivity(Intent(Intent.ACTION_VIEW, url))
            } catch (_: ActivityNotFoundException) {
                Toast.makeText(this, R.string.acute_no_issue_handler, Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            finish()
        }
    }
}
