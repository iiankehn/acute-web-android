plugins { id("com.android.application") }
android {
    namespace = "com.acuteweb.nativeapp"
    compileSdk { version = release(37) }
    defaultConfig {
        // Deliberately cannot replace stable/beta profiles during migration development.
        applicationId = "com.acuteweb.browser.dev"
        minSdk = 31
        targetSdk = 35
        versionCode = providers.environmentVariable("GITHUB_RUN_NUMBER").map { it.toInt() }.orElse(1).get()
        versionName = "2.0.0-dev.1"
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildTypes { release { isMinifyEnabled = false } }
}
dependencies {
    implementation(project(":browser-core"))
    implementation("org.mozilla.geckoview:geckoview:157.0.20261005135250")
}
