package org.mozilla.fenix.acute

import android.app.Activity
import android.app.AlertDialog
import android.app.Application
import android.content.ActivityNotFoundException
import android.content.ContentProvider
import android.content.ContentValues
import android.content.Intent
import android.database.Cursor
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.widget.Toast
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.lang.ref.WeakReference
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Lightweight GitHub Releases update check with no Fenix-internal dependency.
 * It checks at most once every six hours and sends the selected APK to Android's normal
 * download/install flow. It never silently installs software.
 */
class GitHubUpdateProvider : ContentProvider(), Application.ActivityLifecycleCallbacks {
    private val worker = Executors.newSingleThreadExecutor()
    private val checkInProgress = AtomicBoolean(false)
    private val main = Handler(Looper.getMainLooper())
    private var currentActivity = WeakReference<Activity>(null)
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
        if (now - prefs.getLong(KEY_LAST_SUCCESS, 0) < CHECK_INTERVAL_MS) return
        if (now - prefs.getLong(KEY_LAST_ATTEMPT, 0) < RETRY_INTERVAL_MS) return
        prefs.edit().putLong(KEY_LAST_ATTEMPT, now).apply()
        var connection: HttpURLConnection? = null
        try {
            connection = URL(RELEASE_API).openConnection() as HttpURLConnection
            connection.connectTimeout = 10_000
            connection.readTimeout = 15_000
            connection.setRequestProperty("Accept", "application/vnd.github+json")
            connection.setRequestProperty("User-Agent", "Acute-Web-Android")
            connection.setRequestProperty("X-GitHub-Api-Version", "2022-11-28")
            if (connection.responseCode !in 200..299) {
                throw IllegalStateException("GitHub returned HTTP ${connection.responseCode}")
            }
            val body = connection.inputStream.use { input ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                var total = 0
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    total += count
                    if (total > MAX_RESPONSE_BYTES) {
                        throw IllegalStateException("GitHub response exceeded size limit")
                    }
                    output.write(buffer, 0, count)
                }
                output.toString(Charsets.UTF_8.name())
            }
            val json = JSONObject(body)
            val version = json.getString("tag_name").removePrefix("v")
            if (!RELEASE_VERSION.matches(version)) {
                throw IllegalStateException("Latest release has an unsupported version")
            }
            val assets = json.getJSONArray("assets")
            val expectedAsset = "acute-web-$version-arm64-v8a.apk"
            var apkUrl: String? = null
            for (index in 0 until assets.length()) {
                val asset = assets.getJSONObject(index)
                val name = asset.getString("name")
                val candidate = asset.getString("browser_download_url")
                val uri = Uri.parse(candidate)
                val trustedDownload = uri.scheme == "https" && uri.host == "github.com"
                if (trustedDownload && name == expectedAsset) {
                    apkUrl = candidate
                    break
                }
            }
            val pageUrl = json.getString("html_url")
            val pageUri = Uri.parse(pageUrl)
            if (pageUri.scheme != "https" || pageUri.host != "github.com") {
                throw IllegalStateException("Release page URL is not trusted")
            }
            val installed = ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName ?: "0"
            prefs.edit().putLong(KEY_LAST_SUCCESS, now).apply()
            if (apkUrl != null && isNewer(version, installed) &&
                now >= prefs.getLong(KEY_REMIND_AFTER, 0)) {
                val release = Release(version, apkUrl, pageUrl)
                main.post {
                    pendingRelease = release
                    showIfReady()
                }
            }
        } catch (error: Exception) {
            Log.i(TAG, "Update check unavailable", error)
        } finally {
            connection?.disconnect()
        }
    }

    private fun showIfReady() {
        val activity = currentActivity.get() ?: return
        val release = pendingRelease ?: return
        if (activity.isFinishing || activity.isDestroyed) return
        pendingRelease = null
        AlertDialog.Builder(activity)
            .setTitle("Acute Web ${release.version} is available")
            .setMessage("Download the signed APK from GitHub, then approve Android's install prompt.")
            .setPositiveButton("Download") { _, _ ->
                openSafely(activity, release.apkUrl)
            }
            .setNeutralButton("Release notes") { _, _ ->
                openSafely(activity, release.pageUrl)
            }
            .setNegativeButton("Later") { _, _ ->
                context?.getSharedPreferences(PREFS, 0)?.edit()
                    ?.putLong(KEY_REMIND_AFTER, System.currentTimeMillis() + REMIND_INTERVAL_MS)?.apply()
            }
            .show()
    }

    override fun onActivityResumed(activity: Activity) {
        currentActivity = WeakReference(activity)
        requestUpdateCheck()
        showIfReady()
    }
    override fun onActivityPaused(activity: Activity) {
        if (currentActivity.get() === activity) currentActivity.clear()
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

    private fun openSafely(activity: Activity, url: String) {
        try {
            activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (error: ActivityNotFoundException) {
            Log.i(TAG, "No activity can open the update link", error)
            Toast.makeText(activity, "Unable to open this link.", Toast.LENGTH_LONG).show()
        }
    }

    private fun isNewer(candidate: String, installed: String): Boolean {
        if (!RELEASE_VERSION.matches(candidate) || !RELEASE_VERSION.matches(installed)) return false
        val left = candidate.split('.').map { it.toInt() }
        val right = installed.split('.').map { it.toInt() }
        for (index in left.indices) {
            val comparison = left[index].compareTo(right[index])
            if (comparison != 0) return comparison > 0
        }
        return false
    }

    private data class Release(val version: String, val apkUrl: String, val pageUrl: String)

    companion object {
        private const val TAG = "AcuteUpdates"
        private const val PREFS = "acute_updates"
        private const val KEY_LAST_SUCCESS = "last_success_ms"
        private const val KEY_LAST_ATTEMPT = "last_attempt_ms"
        private const val KEY_REMIND_AFTER = "remind_after_ms"
        private const val CHECK_INTERVAL_MS = 6L * 60 * 60 * 1000
        private const val RETRY_INTERVAL_MS = 60L * 60 * 1000
        private const val REMIND_INTERVAL_MS = 24L * 60 * 60 * 1000
        private const val MAX_RESPONSE_BYTES = 1024 * 1024
        private val RELEASE_VERSION = Regex("^[0-9]+\\.[0-9]+\\.[0-9]+$")
        private const val RELEASE_API =
            "https://api.github.com/repos/iiankehn/acute-web-android/releases/latest"
    }
}
