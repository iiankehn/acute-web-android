pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google(); mavenCentral()
        exclusiveContent {
            forRepository { maven { url = uri("https://maven.mozilla.org/maven2/") } }
            filter { includeGroup("org.mozilla.geckoview") }
        }
    }
}
rootProject.name = "AcuteNative"
include(":app", ":browser-core")
