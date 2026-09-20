package org.mozilla.fenix.acute

import android.app.Activity
import android.app.AlertDialog
import android.app.Application
import android.content.ContentProvider
import android.content.ContentValues
import android.content.Intent
import android.database.Cursor
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Lightweight GitHub Releases update check with no Fenix-internal dependency.
 * It checks at most once per day and sends the selected APK to Android's normal
 * download/install flow. It never silently installs software.
 */
class GitHubUpdateProvider : ContentProvider(), Application.ActivityLifecycleCallbacks {
    private val worker = Executors.newSingleThreadExecutor()
    private val checkInProgress = AtomicBoolean(false)
    private val main = Handler(Looper.getMainLooper())
    private var currentActivity: Activity? = null
    private var pendingRelease: Release? = null

    override fun onCreate(): Boolean {
        val app = context?.applicationContext as? Application ?: return false
        app.registerActivityLifecycleCallbacks(this)
        requestUpdateCheck()
        return true
    }

    private fun requestUpdateCheck() {
        if (!checkInProgress.compareAndSet(false, true)) return
        worker.execute {
            try {
                checkForUpdate()
            } finally {
                checkInProgress.set(false)
            }
        }
    }

    private fun checkForUpdate() {
        val ctx = context ?: return
        val prefs = ctx.getSharedPreferences(PREFS, 0)
        val now = System.currentTimeMillis()
        if (now - prefs.getLong(KEY_LAST_CHECK, 0) < CHECK_INTERVAL_MS) return
        try {
            val connection = URL(RELEASE_API).openConnection() as HttpURLConnection
            connection.connectTimeout = 10_000
            connection.readTimeout = 15_000
            connection.setRequestProperty("Accept", "application/vnd.github+json")
            connection.setRequestProperty("User-Agent", "Acute-Web-Android")
            connection.setRequestProperty("X-GitHub-Api-Version", "2022-11-28")
            if (connection.responseCode !in 200..299) {
                throw IllegalStateException("GitHub returned HTTP ${connection.responseCode}")
            }
            val body = connection.inputStream.bufferedReader().use { it.readText() }
            val json = JSONObject(body)
            val version = json.getString("tag_name").removePrefix("v")
            val assets = json.getJSONArray("assets")
            var bestUrl: String? = null
            for (index in 0 until assets.length()) {
                val asset = assets.getJSONObject(index)
                val name = asset.getString("name").lowercase()
                val candidate = asset.getString("browser_download_url")
                val uri = Uri.parse(candidate)
                val trustedDownload = uri.scheme == "https" && uri.host == "github.com"
                if (trustedDownload && name.endsWith(".apk") &&
                    (bestUrl == null || name.contains("universal") || name.contains("arm64-v8a"))) {
                    bestUrl = candidate
                }
            }
            val installed = ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName ?: "0"
            prefs.edit().putLong(KEY_LAST_CHECK, now).apply()
            if (bestUrl != null && isNewer(version, installed) &&
                now >= prefs.getLong(KEY_REMIND_AFTER, 0)) {
                pendingRelease = Release(version, bestUrl, json.getString("html_url"))
                main.post { showIfReady() }
            }
        } catch (error: Exception) {
            Log.i(TAG, "Update check unavailable", error)
        }
    }

    private fun showIfReady() {
        val activity = currentActivity ?: return
        val release = pendingRelease ?: return
        if (activity.isFinishing || activity.isDestroyed) return
        pendingRelease = null
        AlertDialog.Builder(activity)
            .setTitle("Acute Web ${release.version} is available")
            .setMessage("Download the signed APK from GitHub, then approve Android's install prompt.")
            .setPositiveButton("Download") { _, _ ->
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(release.apkUrl))
                activity.startActivity(intent)
            }
            .setNeutralButton("Release notes") { _, _ ->
                activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(release.pageUrl)))
            }
            .setNegativeButton("Later") { _, _ ->
                context?.getSharedPreferences(PREFS, 0)?.edit()
                    ?.putLong(KEY_REMIND_AFTER, System.currentTimeMillis() + REMIND_INTERVAL_MS)?.apply()
            }
            .show()
    }

    override fun onActivityResumed(activity: Activity) {
        currentActivity = activity
        requestUpdateCheck()
        showIfReady()
    }
    override fun onActivityPaused(activity: Activity) {
        if (currentActivity === activity) currentActivity = null
    }
    override fun onActivityCreated(activity: Activity, state: Bundle?) = Unit
    override fun onActivityStarted(activity: Activity) = Unit
    override fun onActivityStopped(activity: Activity) = Unit
    override fun onActivitySaveInstanceState(activity: Activity, state: Bundle) = Unit
    override fun onActivityDestroyed(activity: Activity) = Unit

    override fun query(uri: Uri, projection: Array<out String>?, selection: String?,
        selectionArgs: Array<out String>?, sortOrder: String?): Cursor? = null
    override fun getType(uri: Uri): String? = null
    override fun insert(uri: Uri, values: ContentValues?): Uri? = null
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int = 0
    override fun update(uri: Uri, values: ContentValues?, selection: String?,
        selectionArgs: Array<out String>?): Int = 0

    private fun isNewer(candidate: String, installed: String): Boolean {
        val left = candidate.split('.', '-', '+').map { it.toIntOrNull() ?: 0 }
        val right = installed.split('.', '-', '+').map { it.toIntOrNull() ?: 0 }
        for (index in 0 until maxOf(left.size, right.size)) {
            val comparison = (left.getOrNull(index) ?: 0).compareTo(right.getOrNull(index) ?: 0)
            if (comparison != 0) return comparison > 0
        }
        return false
    }

    private data class Release(val version: String, val apkUrl: String, val pageUrl: String)

    companion object {
        private const val TAG = "AcuteUpdates"
        private const val PREFS = "acute_updates"
        private const val KEY_LAST_CHECK = "last_check_ms"
        private const val KEY_REMIND_AFTER = "remind_after_ms"
        private const val CHECK_INTERVAL_MS = 6L * 60 * 60 * 1000
        private const val REMIND_INTERVAL_MS = 24L * 60 * 60 * 1000
        private const val RELEASE_API =
            "https://api.github.com/repos/iiankehn/acute-web-android/releases/latest"
    }
}
