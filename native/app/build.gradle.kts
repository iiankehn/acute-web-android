plugins { id("com.android.application") }
android {
    namespace = "com.acuteweb.nativeapp"
    compileSdk { version = release(37) }
    defaultConfig {
        // Deliberately cannot replace stable/beta profiles during migration development.
        applicationId = "com.acuteweb.browser.dev"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        minSdk = 31
        targetSdk = 35
        versionCode = providers.environmentVariable("GITHUB_RUN_NUMBER").map { it.toInt() }.orElse(1).get()
        versionName = "2.0.0-dev.5"
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildTypes { release { isMinifyEnabled = false } }
}
dependencies {
    implementation("androidx.core:core-ktx:1.19.0")
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.test:core:1.7.0")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    implementation(project(":browser-core"))
    implementation("org.mozilla.geckoview:geckoview:157.0.20261005135250")
}

// Places' maintained native binding is used directly; Glean/Sync initialization is not part of Dev.
configurations.configureEach { exclude(group = "org.mozilla.telemetry") }
dependencies { implementation("org.mozilla.appservices:places:157.0.1") }

val verifyDevDependencies by tasks.registering {
    doLast {
        val modules = configurations.getByName("debugRuntimeClasspath").incoming.resolutionResult.allComponents
            .mapNotNull { it.id as? org.gradle.api.artifacts.component.ModuleComponentIdentifier }
        check(modules.none { it.group == "org.mozilla.telemetry" || it.group.startsWith("com.adjust") }) {
            "Telemetry artifacts are forbidden in the Dev runtime"
        }
    }
}
