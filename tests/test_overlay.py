from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from apply_overlay import apply, OverlayError  # noqa: E402


GRADLE = '''import com.android.build.api.variant.FilterConfiguration
android {
    defaultConfig {
        applicationId "org.mozilla"
    }
    def releaseTemplate = {
        signingConfig = signingConfigs.debug
    }
    buildTypes {
        debug {
            applicationIdSuffix ".fenix.debug"
        }
        beta releaseTemplate >> {
            applicationIdSuffix ".firefox_beta"
            manifestPlaceholders.putAll([
                    "sharedUserId": "org.mozilla.firefox.sharedID",
            ])
        }
        release releaseTemplate >> {
            applicationIdSuffix ".firefox"
            manifestPlaceholders.putAll([
                    "sharedUserId": "org.mozilla.firefox.sharedID",
            ])
        }
    }
    splits {
        abi {
            if (gradle.mozconfig.substs.MOZILLA_OFFICIAL || System.getenv("MOZ_BUILD_CONFIG_LINT") == "1") {
                universalApk true
            }
        }
    }
}
androidComponents {
    onVariants(selector().all()) { variant ->
        def buildType = variant.buildType
        if (buildType in ['nightly', 'beta', 'release', 'benchmark']) {
            variant.outputs.each { output ->
                output.versionName.set("test")
            }
        }
    }
}
android.defaultConfig.with {
    buildConfigField 'boolean', 'CRASH_REPORTING', 'true'
    buildConfigField 'boolean', 'TELEMETRY', 'true'
}
'''

MANIFEST = '''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <!-- Needed to get distribution information from partners.
    This is NOT required for the adjust plugin. -->
    <uses-permission android:name="com.adjust.preinstall.READ_PERMISSION"/>

    <!-- Needed for Google Play policy https://support.google.com/googleplay/android-developer/answer/6048248 -->
    <uses-permission android:name="com.google.android.gms.permission.AD_ID"/>

    <!-- Needed to interact with all apps installed on a device -->
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"
        tools:ignore="QueryAllPackagesPermission" />

    <!-- Needed to prompt the user directly for app uninstallation as part of an
    'uninstall survey' experiment. This is ONLY used to uninstall the Firefox application -->
    <uses-permission android:name="android.permission.REQUEST_DELETE_PACKAGES" tools:node="replace" />

    <uses-permission-sdk-23 android:name="android.permission.REQUEST_INSTALL_PACKAGES" />

    <application
        android:label="@string/app_name">
        <activity android:name=".HomeActivity" android:resizeableActivity="true" />
    </application>
</manifest>
'''

CHANNEL_MANIFEST = '''<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    android:sharedUserId="${sharedUserId}">
</manifest>
'''

SETTINGS = '''package org.mozilla.fenix.utils
class Settings(private val appContext: Context) {
    @Suppress("DEPRECATION")
    var showPocketRecommendationsFeature by
        lazyFeatureFlagBooleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_pocket_homescreen_recommendations),
            featureFlag = ContentRecommendationsFeatureHelper.isContentRecommendationsFeatureEnabled(appContext),
            defaultValue = { homescreenSections[HomeScreenSection.POCKET] == true },
        )

    var crashReportChoice by
        stringPreference(
            appContext.getPreferenceKey(R.string.pref_key_crash_reporting_choice),
            default = CrashReportOption.Ask.toString(),
        )

    var isMarketingTelemetryEnabled by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_marketing_telemetry),
            default = false,
        )

    var shouldUseLightTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_light_theme),
            default = false,
        )

    var shouldUseDarkTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_dark_theme),
            default = false,
        )

    var shouldUseOledTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_oled_theme),
            default = false,
        )

    var shouldFollowDeviceTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_follow_device_theme),
            default = false,
        )

    var shouldUseExpandedToolbar by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_toolbar_expanded),
            default = { FxNimbus.features.defaultExpandedToolbar.value().enabled },
            persistDefaultIfNotExists = true,
        )

    var isTabStripEnabled by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_tab_strip_show),
            default =
                FxNimbus.features.tabStrip.value().enabled &&
                    (isTabStripEligible(appContext) || FxNimbus.features.tabStrip.value().allowOnAllDevices),
        )

    var showContileFeature by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_enable_contile),
            default = true,
        )

    var currentWallpaperName by
        stringPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_current_wallpaper),
            default =
                if (enableHomepageEdgeToEdgeBackgroundFeature) {
                    Wallpaper.EdgeToEdge.name
                } else {
                    Wallpaper.Default.name
                },
        )

    val shouldUseAutoBatteryTheme by
        booleanPreference(
            appContext.getPreferenceKey(R.string.pref_key_auto_battery_theme),
            default = false,
        )

    var tabGroupsEnabled by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_tab_groups),
            default = { DefaultTabManagementFeatureHelper.tabGroupsEnabled },
        )

    var showTabGroupsInMenu by
        booleanPreference(
            key = appContext.getPreferenceKey(R.string.pref_key_show_tab_groups_in_menu),
            default = { DefaultTabManagementFeatureHelper.showTabGroupsInMenu },
        )
}
'''

ONBOARDING = '''class OnboardingFragment {
    private val pagesToDisplay by lazy {
        allOnboardingPages
            .filterNot {
                it.type == OnboardingPageUiData.Type.MARKETING_DATA &&
                    !requireComponents.settings.shouldShowMarketingOnboarding
            }
            .distinctBy { it.type }
            .toMutableStateList()
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        addMarketingFeature.set(
            feature =
                MarketingPageAdditionSupport(
                    prefKey = requireContext().getString(R.string.pref_key_should_show_marketing_onboarding),
                    pagesToDisplay = pagesToDisplay,
                    marketingPage = marketingPage,
                    settings = requireComponents.settings,
                    lifecycleOwner = viewLifecycleOwner,
                ),
            owner = this,
            view = view,
        )
        super.onViewCreated(view, savedInstanceState)
    }
}
'''

PREFERENCES = '''<PreferenceScreen xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">
        <androidx.preference.Preference
            android:key="@string/pref_key_data_choices"
            app:iconSpaceReserved="false"
            android:title="@string/preferences_data_collection" />
</PreferenceScreen>
'''

SEARCH_PROVIDERS = '''import org.mozilla.fenix.settings.datachoices.DataChoicesSearchProvider

class SettingsSearchProviders {
    val providers = listOf(
        DataChoicesSearchProvider,
    )
}
'''

DESKTOP_MODE = '''class DefaultDesktopModeRepository(private val context: Context) {
    internal val defaultDesktopMode by lazy {
        context.isLargeScreenSize()
    }
}
'''

WORDMARK = '''import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp

@Composable
internal fun WordmarkText(color: Color?) {
    Image(
        modifier =
            Modifier.semantics {
                    testTagsAsResourceId = true
                    testTag = HOMEPAGE_WORDMARK_TEXT
                }
                .height(dimensionResource(R.dimen.wordmark_text_height)),
        painter = painterResource(getAttr(R.attr.fenixWordmarkText)),
        colorFilter = color?.let { ColorFilter.tint(it) },
        contentDescription = stringResource(R.string.app_name),
    )
}
'''

COLORS = '''<resources>
<color name="fx_mobile_primary">@color/novaViolet70</color>
<color name="fx_mobile_primary_container">@color/novaViolet20</color>
<color name="fx_mobile_tertiary">@color/novaViolet50</color>
<color name="fx_mobile_splashscreen_background">#FCF3EE</color>
<color name="fx_mobile_private_primary">@color/novaViolet20</color>
<color name="fx_mobile_private_primary_container">@color/novaViolet60</color>
<color name="fx_mobile_private_background">@color/novaVioletDesaturated90</color>
<color name="fx_mobile_private_surface">@color/novaVioletDesaturated90</color>
<color name="fx_mobile_private_surface_variant">@color/novaVioletDesaturated80</color>
</resources>'''

NIGHT_COLORS = '''<resources>
<color name="fx_mobile_primary">@color/novaViolet20</color>
<color name="fx_mobile_on_primary">@color/novaGray80</color>
<color name="fx_mobile_primary_container">@color/novaViolet60</color>
<color name="fx_mobile_on_primary_container">@color/novaVioletDesaturated0</color>
<color name="fx_mobile_secondary">@color/novaGray20</color>
<color name="fx_mobile_on_secondary">@color/novaGray80</color>
<color name="fx_mobile_secondary_container">@color/novaVioletDesaturated70</color>
<color name="fx_mobile_on_secondary_container">@color/novaVioletDesaturated0</color>
<color name="fx_mobile_tertiary">@color/novaViolet30</color>
<color name="fx_mobile_on_tertiary">@color/novaGray80</color>
<color name="fx_mobile_tertiary_container">@color/novaVioletDesaturated90</color>
<color name="fx_mobile_on_tertiary_container">@color/novaVioletDesaturated0</color>
<color name="fx_mobile_background">@color/novaGray75</color>
<color name="fx_mobile_on_background">@color/novaVioletDesaturated0</color>
<color name="fx_mobile_surface">@color/novaGray75</color>
<color name="fx_mobile_on_surface">@color/novaVioletDesaturated0</color>
<color name="fx_mobile_surface_variant">@color/novaGray65</color>
<color name="fx_mobile_on_surface_variant">@color/novaVioletDesaturated0A70</color>
<color name="fx_mobile_outline">@color/novaGray45</color>
<color name="fx_mobile_surface_bright">@color/novaGray65</color>
<color name="fx_mobile_surface_dim">@color/novaGray85</color>
<color name="fx_mobile_surface_container">@color/novaGray75</color>
<color name="fx_mobile_surface_container_high">@color/novaGray70</color>
<color name="fx_mobile_surface_container_highest">@color/novaGray65</color>
<color name="fx_mobile_surface_container_low">@color/novaGray80</color>
<color name="fx_mobile_surface_container_lowest">@color/novaGray85</color>
<color name="fx_mobile_surface_container_selected">@color/novaGray55</color>
</resources>'''

BROWSER_TOOLBAR = '''import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color

class BrowserToolbarComposable {
    fun Content() {
                    MaterialTheme(colorScheme = colorScheme) {
                        when (!shouldUseBottomToolbar) {
                            true ->
                                Column(modifier = Modifier.fillMaxWidth().wrapContentHeight()) {
                                }
                            false ->
                                Column(modifier = Modifier.fillMaxWidth().wrapContentHeight()) {
                                }
                        }
                    }
    }
}
'''

FULL_DISPLAY_TOOLBAR = '''import androidx.compose.foundation.background
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

fun FullDisplayToolbar() {
    Modifier
                            .background(
                                color = MaterialTheme.colorScheme.surfaceContainerHighest,
                                shape = CircleShape,
                            )
}
'''

BROWSER_EDIT_TOOLBAR = '''import androidx.compose.foundation.background
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

fun BrowserEditToolbar() {
    Modifier
                        .clip(shape = CircleShape)
                        .background(color = MaterialTheme.colorScheme.surfaceContainerHighest),
}
'''

COMPOSE_BROWSER_TOOLBAR = '''import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.graphics.Color

fun BrowserToolbar() {
    val backgroundColor = MaterialTheme.colorScheme.surface
}
'''

BASE_BROWSER_FRAGMENT = '''import org.mozilla.fenix.utils.allowUndo

class BaseBrowserFragment {
    fun initializeEngineView(topToolbarHeight: Int, bottomToolbarHeight: Int) {
        val context = requireContext()

        if (isToolbarDynamic(context) && webAppToolbarShouldBeVisible) {
            getEngineView().setDynamicToolbarMaxHeight(topToolbarHeight + bottomToolbarHeight)

            (getSwipeRefreshLayout().layoutParams as CoordinatorLayout.LayoutParams).behavior =
                EngineViewClippingBehavior(
                    context = context,
                    attrs = null,
                    engineViewParent = getSwipeRefreshLayout(),
                    topToolbarHeight = topToolbarHeight,
                    bottomToolbarHeight = bottomToolbarHeight,
                )
        } else {
            getEngineView().setDynamicToolbarMaxHeight(0)
            val swipeRefreshParams = getSwipeRefreshLayout().layoutParams as CoordinatorLayout.LayoutParams
            swipeRefreshParams.topMargin = topToolbarHeight
            swipeRefreshParams.bottomMargin = bottomToolbarHeight
        }
    }
}
'''

BROWSER_FRAGMENT = '''import android.content.Context
import android.view.View
import kotlinx.coroutines.Dispatchers

class BrowserFragment {
    fun getContextMenuCandidates(context: Context, view: View): List<ContextMenuCandidate> {
        return if (nativeShareSheetEnabled) {
            NativeShareSheetContextMenuCandidate.defaultCandidates()
        } else {
            ContextMenuCandidate.defaultCandidates()
        } +
            createOpenInExternalAppCandidate(
                requireContext(),
                contextMenuCandidateAppLinksUseCases,
            ) +
            createOpenWithGoogleLensCandidate(context)
    }

    private fun navigateToShareFragment(
        currentTab: SessionState,
        hitTabUrl: String,
    ) {}

    private fun String.isHttpUrl(): Boolean =
        startsWith("https://", ignoreCase = true) || startsWith("http://", ignoreCase = true)
}
'''

NATIVE_CONTEXT_MENU_CANDIDATES = '''object NativeShareSheetContextMenuCandidate {
    fun defaultCandidates() =
        listOf(
            createCopyLinkCandidate(context, snackBarParentView, snackbarDelegate),
            createCopyLinkTextCandidate(context, snackBarParentView, snackbarDelegate),
            createDownloadLinkCandidate(context, contextMenuUseCases, downloadsLocation),
            createShareLinkCandidate(
                context = context,
                shareUseCases = shareUseCases,
                shareItems = getShareItems,
                navigateToShareFragment = navigateToShareFragment,
            ),
            createShareImageCandidate(context, contextMenuUseCases),
        )
}
'''

COMPONENT_CONTEXT_MENU_CANDIDATES = '''data class ContextMenuCandidate(val id: String) {
    companion object {
        fun defaultCandidates() =
            listOf(
                createCopyLinkCandidate(context, snackBarParentView, snackbarDelegate),
                createCopyLinkTextCandidate(context, snackBarParentView, snackbarDelegate),
                createDownloadLinkCandidate(context, contextMenuUseCases, downloadsLocation),
                createShareLinkCandidate(context),
                createShareImageCandidate(context, contextMenuUseCases),
            )
    }
}
'''

ENGINE_VIEW_CLIPPING_BEHAVIOR = '''class EngineViewClippingBehavior(
    private val engineViewParent: View,
    private val topToolbarHeight: Int,
    private val bottomToolbarHeight: Int,
) {
    private var recentBottomToolbarTranslation: Float = 0f
    private var recentTopToolbarTranslation: Float = 0f
    private val dynamicToolbarMaxHeight = topToolbarHeight + bottomToolbarHeight

    fun update(recentTopToolbarTranslation: Float) {
        if (topToolbarHeight > 0) {
                engineViewParent.translationY = recentTopToolbarTranslation + topToolbarHeight
        }
            val contentBottomClipping = (recentTopToolbarTranslation - recentBottomToolbarTranslation).roundToInt()
    }
}
'''

TOOLBAR_BEHAVIOR_CONTROLLER = '''class ToolbarBehaviorController {
    private lateinit var toolbar: ScrollableToolbar

    fun update(state: State) {
        if (state.content.loading) {
            expandToolbar()
            disableScrolling()
                        } else if (!state.content.loading) {
                            enableScrolling()
                        }
    }
}
'''

HOME_ACTIVITY = '''import android.view.KeyEvent
import android.view.MotionEvent
import org.mozilla.fenix.ext.setNavigationIcon

class HomeActivity {
    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
        return super.dispatchTouchEvent(ev)
    }

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (event.action == KeyEvent.ACTION_DOWN && event.keyCode == KeyEvent.KEYCODE_MENU) {
            openMenu()
        }
        return super.dispatchKeyEvent(event)
    }

    final override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        return super.onKeyDown(keyCode, event)
    }
}
'''

MAIN_MENU = '''fun MainMenu(
    accessPoint: MenuAccessPoint,
    onShareButtonClick: () -> Unit,
    extensionsMenuItemDescription: String?,
    moreSettingsSubmenu: @Composable () -> Unit,
    extensionSubmenu: @Composable () -> Unit,
) {
        if (accessPoint == MenuAccessPoint.Home && showBanner) {
            MenuBanner(
                onDismiss = {
                    onBannerDismiss()
                },
                onClick = {
                    onBannerClick()
                },
            )
        }

        if (showIPProtection) {
            MenuGroup {
                IPProtectionMenuItem(
                    state = ipProtectionMenuState,
                    onToggle = onIPProtectionClick,
                    onNavigate = onIPProtectionNavigate,
                )
            }
        }

        if (accessPoint == MenuAccessPoint.Home) {
            MenuGroup {
                ExtensionsMenuItem(
                    inCustomTab = false,
                )
            }
        }

        if (accessPoint == MenuAccessPoint.Browser) {
            ToolsAndActionsMenuGroup(
                onFindInPageMenuClick = onFindInPageMenuClick,
                moreSettingsSubmenu = moreSettingsSubmenu,
                extensionSubmenu = extensionSubmenu,
            )
        }

        LibraryMenuGroup(
            isDownloadHighlighted = isDownloadHighlighted,
            onBookmarksMenuClick = onBookmarksMenuClick,
            onHistoryMenuClick = onHistoryMenuClick,
            onDownloadsMenuClick = onDownloadsMenuClick,
            onPasswordsMenuClick = onPasswordsMenuClick,
        )

        MenuGroup {
            MozillaAccountMenuItem(
                account = account,
                accountState = accountState,
                onClick = onMozillaAccountButtonClick,
            )

            if (accessPoint == MenuAccessPoint.Home) {
                MenuItem(label = "Customize")
            }

            MenuItem(label = "Settings")
        }
}

private fun ToolsAndActionsMenuGroup(
    onFindInPageMenuClick: () -> Unit,
    moreSettingsSubmenu: @Composable () -> Unit,
    extensionSubmenu: @Composable () -> Unit,
) {
    MenuGroup {
        MenuItem(
            label = stringResource(id = R.string.browser_menu_find_in_page),
            beforeIconPainter = painterResource(id = iconsR.drawable.mozac_ic_search_24),
            onClick = onFindInPageMenuClick,
        )
    }
}
'''

MENU_DIALOG = '''import org.mozilla.fenix.utils.exitSubmenu

fun MenuDialog() {
    MenuDialogBottomSheet(
                menuHandleState =
                    MenuHandleState(
                        contentDescription = handlebarContentDescription,
                        useDarkBackground =
                            !settings.shouldUseBottomToolbar &&
                                !settings.shouldUseExpandedToolbar &&
                                (isExtensionsExpanded || isMoreMenuExpanded) &&
                                args.accesspoint == MenuAccessPoint.Browser,
                    ),
                snackbarHostState = snackbarHostState,
                cornerShape =
                    MaterialTheme.shapes.extraLarge.copy(
                        bottomStart = CornerSize(0.dp),
                        bottomEnd = CornerSize(0.dp),
                    ),
    ) {}

    MainMenu(
                                moreSettingsSubmenu = {
                                    MoreSettingsSubmenu(
                                        isAndroidAutomotiveAvailable = context.isAndroidAutomotiveAvailable(),
                                        summarizationMenuState = summarizationMenuState,
                                    )
                                },
    )
}
'''

MORE_SETTINGS = '''fun MoreSettingsSubmenu(
    isAndroidAutomotiveAvailable: Boolean,
    summarizationMenuState: SummarizationMenuState,
    onSaveAsPDFMenuClick: () -> Unit,
    onPrintMenuClick: () -> Unit,
) {
    Column {
        SaveAsPdfMenuItem(onSaveAsPDFMenuClick = onSaveAsPDFMenuClick)
        PrintMenuItem(
            isAndroidAutomotiveAvailable = isAndroidAutomotiveAvailable,
            onPrintMenuClick = onPrintMenuClick,
        )
    }
}
'''

TAB_STORAGE_MIDDLEWARE = '''class TabStorageMiddleware(
    private val mainScope: CoroutineScope = CoroutineScope(Dispatchers.Main),
) : Middleware<TabsTrayState, TabsTrayAction> {
    fun processAction(action: TabsStorageAction) {
        when (action) {
            is TabGroupAction.CloseTabGroupClicked -> {
                scope.launch {
                    tabGroupRepository.closeTabGroup(tabGroupId = action.group.id)
                }
            }
        }
    }
}
'''

TAB_MANAGEMENT_FRAGMENT = '''import mozilla.components.browser.state.selector.privateTabs

class TabManagementFragment {
    fun createStore() {
        TabStorageMiddleware(
                            inactiveTabsEnabled = requireComponents.settings.inactiveTabsAreEnabled,
                            tabGroupsEnabled = requireComponents.settings.tabGroupsEnabled,
                            tabDataFlow = requireComponents.core.store.stateFlow.map { TabData(it) },
                            tabGroupRepository = requireComponents.core.tabGroupRepository,
                            removeTabsUseCase = requireComponents.useCases.tabsUseCases.removeTabs,
                            moveTabsUseCase = requireComponents.useCases.tabsUseCases.moveTabs,
                            fenixBrowserUseCases = requireComponents.useCases.fenixBrowserUseCases,
                            mainScope = lifecycleScope,
        )
    }
}
'''

HOMEPAGE = '''import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize

fun Homepage(state: HomepageState, interactor: HomepageInteractor) {
            if (state is HomepageState.Normal) {
                BannerCardSection(
                    shouldShowPrivacyNoticeBanner = state.shouldShowPrivacyNoticeBanner,
                    nimbusMessage = state.nimbusMessage,
                    privacyNoticeBannerInteractor = interactor,
                    messageCardInteractor = interactor,
                )
            }

            when (val headerState = state.headerState) {
                is HeaderState.Experimental.Normal -> {
                    ExperimentalHomepageHeader(
                        showStoriesButton = headerState.showStoriesButton,
                    )
                }
                is HeaderState.Experimental.Private -> {
                    ExperimentalPrivateHomepageHeader()
                }
                is HeaderState.Normal -> {
                    HomepageHeader(
                        browsingMode = state.browsingMode,
                        browsingModeChanged = browsingModeChanged,
                    )
                }
            }

            if (state.firstFrameDrawn) {
                with(state) {
                    when (this) {
                        is HomepageState.Private -> {
                            PrivateBrowsingDescription()
                        }
                        is HomepageState.Normal -> {
                            val context = LocalContext.current

                            LaunchedEffect(showLongfoxAnimation) {
                                showAnimation()
                            }

                            val longfoxEntryPointShown = longfoxEnabled && showPrivacyReport

                            if (topSiteState != null) {
                                TopSitesSection(state = topSiteState)
                            }

                            if (showPrivacyReport) {
                                TrackersBlockedCard(
                                    trackersBlockedCount = trackersBlockedCount,
                                )
                            }

                            MaybeAddSetupChecklist(setupChecklistState, interactor)

                            if (recentTabs != null) {
                                RecentTabsSection(
                                    interactor = interactor,
                                    recentTabs = recentTabs,
                                    reducedTopSpacing = showPrivacyReport && showLongfoxAnimation,
                                )

                                when (val syncedTabState = recentSyncedTabSectionState) {
                                    RecentSyncedTabSectionState.Gone -> Unit
                                }
                            }

                            if (bookmarks != null) {
                                BookmarksSection(
                                    bookmarks = bookmarks,
                                    interactor = interactor,
                                )
                            }

                            if (recentlyVisited != null) {
                                RecentlyVisitedSection(
                                    recentVisits = recentlyVisited,
                                    interactor = interactor,
                                )
                            }

                            CollectionsSection(
                                collectionsState = collectionsState,
                                interactor = interactor,
                                onCollectionsMigrationCardAction = onCollectionsMigrationCardAction,
                            )

                            if (pocketState != null) {
                                Spacer(Modifier.weight(1f))
                                PocketSection(
                                    state = pocketState,
                                    interactor = interactor,
                                )
                            }

                            Spacer(Modifier.height(bottomPadding.dp))

                            val popularSites = observePopularSites(topSites = topSiteState?.topSites)

                            when (shortcutsDialogState) {
                                DialogState.Closed -> Unit
                            }
                        }
                    }
                }
            }
}

@Composable
private fun CollectionsSection(
    collectionsState: CollectionsState,
    interactor: CollectionInteractor,
    onCollectionsMigrationCardAction: (CollectionsMigrationCardAction) -> Unit,
) {
    when (collectionsState) {
        is CollectionsState.Content -> {
            CollectionsSectionContent {
                Collections(
                    collections = collectionsState.collections,
                    expandedCollections = collectionsState.expandedCollections,
                    showAddTabToCollection = collectionsState.showSaveTabsToCollection,
                    interactor = interactor,
                )
            }
        }

        CollectionsState.MigrationCard -> {
            CollectionsSectionContent {
                CollectionsMigrationPromoCard(onClick = { onCollectionsMigrationCardAction(ViewTabGroupsClicked) })
            }
        }

        CollectionsState.Gone -> {} // no-op. Nothing is shown where there are no collections.
    }
}
'''

WORKSPACE_STRINGS = '''
<string name="browser_menu_add_to_tab_group">Add to group</string>
<string name="preferences_tab_groups_feature">Enable Tab Groups</string>
<string name="create_tab_group_content_description">Create tab group</string>
<string name="tab_manager_multiselect_menu_item_add_to_tab_group">Add to group</string>
<string name="tab_group_onboarding_item_title">Create a tab group</string>
<string name="tab_group_onboarding_grid_item_description">Drag one tab onto another to group them.</string>
<string name="tab_group_onboarding_list_item_description">Select multiple tabs to create a group.</string>
<string name="tab_group_onboarding_item_dismiss_content_description">Dismiss tab group onboarding</string>
<string name="tab_manager_empty_tab_groups_page_header">Try tab groups</string>
<string name="tab_manager_empty_tab_groups_page_description">Select tabs to create a group.</string>
<string name="create_tab_group_title">Create tab group</string>
<string name="edit_tab_group_title">Edit group</string>
<string name="edit_tab_group_bottom_sheet_grabber_content_description">New group, collapse drag handle</string>
<string name="create_tab_group_form_default_name">Group %d</string>
<string name="add_to_tab_group_title">Add to</string>
<string name="add_to_tab_group_bottom_sheet_grabber_content_description">Add to a tab group, collapse drag handle</string>
<string name="add_to_new_tab_group_content_description">Add to new tab group</string>
<string name="add_to_new_tab_group_title">New tab group</string>
<string name="tab_group_sheet_dismiss_description">View tab group, collapse drag handle</string>
<string name="delete_tab_group_confirmation_dialog_title">Delete tab group?</string>
<string name="delete_tab_group_confirmation_dialog_body">This deletes the group permanently.</string>
<string name="delete_tab_group_confirmation_dialog_confirm">Delete group</string>
<string name="close_tab_and_delete_group_confirmation_dialog_title">Close tab and delete group?</string>
<string name="close_tab_and_delete_group_confirmation_dialog_body">This deletes the group permanently.</string>
<string name="close_tab_and_delete_group_confirmation_dialog_confirm">Delete group</string>
<string name="tab_group_three_dot_menu_close">Close</string>
<string name="tab_group_three_dot_menu_ungroup">Ungroup</string>
<string name="ungroup_tab_group_confirmation_dialog_title">Ungroup tab group?</string>
<string name="ungroup_tab_group_confirmation_dialog_body">The tabs remain open.</string>
<string name="ungroup_tab_group_confirmation_dialog_confirm">Ungroup</string>
<string name="collections_migration_homepage_banner_title">Collections are now groups</string>
<string name="collections_migration_homepage_card_message">Keep tabs organized</string>
<string name="collections_migration_homepage_card_link">View my tab groups</string>
<plurals name="tabs_header_tab_group_counter_title">
<item quantity="one">%1$d tab group open.</item>
<item quantity="other">%1$d tab groups open.</item>
</plurals>
<plurals name="add_to_exiting_tab_group_content_description">
<item quantity="one">Add to %1$s tab group, %2$d tab, color %3$s</item>
<item quantity="other">Add to %1$s tab group, %2$d tabs, color %3$s</item>
</plurals>
<plurals name="expanded_tab_group_header_description">
<item quantity="one">%1$s tab group with %2$d tab, color %3$s</item>
<item quantity="other">%1$s tab group with %2$d tabs, color %3$s</item>
</plurals>
'''

CUSTOMIZATION = '''<androidx.preference.PreferenceScreen>
    <androidx.preference.PreferenceCategory
        android:layout="@layout/preference_cat_style"
        android:title="@string/preferences_theme"
        app:iconSpaceReserved="false">
        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="@bool/underAPI28"
            android:key="@string/pref_key_light_theme"
            android:title="@string/preference_light_theme" />

        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="false"
            android:key="@string/pref_key_dark_theme"
            android:title="@string/preference_dark_theme" />

        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="false"
            android:key="@string/pref_key_oled_theme"
            android:title="@string/preference_oled_theme"
            android:visible="false" />

        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="false"
            android:key="@string/pref_key_auto_battery_theme"
            android:title="@string/preference_auto_battery_theme"
            app:isPreferenceVisible="@bool/underAPI28" />

        <org.mozilla.fenix.settings.RadioButtonPreference
            android:defaultValue="@bool/API28"
            android:key="@string/pref_key_follow_device_theme"
            android:title="@string/preference_follow_device_theme"
            app:isPreferenceVisible="@bool/API28" />
    </androidx.preference.PreferenceCategory>

    <androidx.preference.PreferenceCategory
        android:layout="@layout/preference_cat_style"
        android:title="@string/preferences_app_icon"
        android:key="@string/pref_key_customization_category_app_icon"
        app:allowDividerBelow="false"
        app:iconSpaceReserved="false">
        <org.mozilla.fenix.iconpicker.ui.AppIconPreference
            android:key="@string/pref_key_app_icon" />
    </androidx.preference.PreferenceCategory>

</androidx.preference.PreferenceScreen>'''

CUSTOMIZATION_FRAGMENT = '''class CustomizationFragment {
    private fun setupPreferences() {
        bindFollowDeviceTheme()
        bindDarkTheme()
        bindDarkestTheme()
        bindLightTheme()
        bindAutoBatteryTheme()
        setupRadioGroups()
        setupToolbarCategory()
    }
}'''

CORE = '''class Core {
    val store = BrowserStore().apply {
                // Install the "icons" WebExtension to automatically load icons for every visited website.
                icons.install(engine, this)
    }
}'''

STYLES = '''<resources>
<style name="NormalTheme">
<item name="accent">@color/accent_normal_theme</item>
<item name="accentBright">@color/photonViolet70</item>
<item name="fenixLogo">@drawable/ic_logo_wordmark_normal</item>
<item name="fenixWordmarkLogo">@drawable/ic_wordmark_logo</item>
</style>
<style name="PrivateTheme">
<item name="fenixLogo">@drawable/ic_logo_wordmark_private</item>
</style>
</resources>'''

ABOUT = '''import android.os.Build
import android.view.View
import org.mozilla.fenix.BuildConfig
import org.mozilla.geckoview.BuildConfig as GeckoViewBuildConfig

class AboutFragment {
    private lateinit var appName: String
    private fun populateAboutHeader() {
        val aboutText =
            try {
                val packageInfo =
                    requireContext()
                        .packageManagerCompatHelper
                        .getPackageInfoCompat(requireContext().packageName, 0)
                val versionCode = PackageInfoCompat.getLongVersionCode(packageInfo).toString()
                val maybeFenixVcsHash = if (BuildConfig.VCS_HASH.isNotBlank()) ", ${BuildConfig.VCS_HASH}" else ""
                val maybeGecko = getString(R.string.gecko_view_abbreviation)
                val geckoVersion = GeckoViewBuildConfig.MOZ_APP_VERSION + "-" + GeckoViewBuildConfig.MOZ_APP_BUILDID
                val appServicesAbbreviation = getString(R.string.app_services_abbreviation)
                val appServicesVersion = mozilla.components.Build.APPLICATION_SERVICES_VERSION
                val operatingSystemAbbrevation = "OS"
                val operatingSystemVersion = "Android ${Build.VERSION.RELEASE}"

                String.format(
                    "%s (Build #%s)%s\\n%s: %s\\n%s: %s\\n%s: %s",
                    packageInfo.versionName,
                    versionCode,
                    maybeFenixVcsHash,
                    maybeGecko,
                    geckoVersion,
                    appServicesAbbreviation,
                    appServicesVersion,
                    operatingSystemAbbrevation,
                    operatingSystemVersion,
                )
            } catch (e: PackageManager.NameNotFoundException) {
                ""
            }

        val content = getString(R.string.about_content, appName)
        val buildDate = BuildConfig.BUILD_DATE

        binding.aboutText.text = aboutText
        binding.aboutContent.text = content
        binding.buildDate.text = buildDate
    }
    private fun populateAboutList(): List<AboutPageItem> {
        val context = requireContext()

        return listOf(
            AboutPageItem(
                AboutItem.ExternalLink(
                    WHATS_NEW,
                    SupportUtils.WHATS_NEW_URL,
                ),
                // Note: Fenix only has release notes for 'Release' versions, NOT 'Beta' & 'Nightly'.
                getString(R.string.about_whats_new, getString(R.string.firefox)),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(
                    SUPPORT,
                    SupportUtils.getSumoURLForTopic(context, SupportUtils.SumoTopic.HELP),
                ),
                getString(R.string.about_support),
            ),
            AboutPageItem(
                AboutItem.Crashes,
                getString(R.string.about_crashes),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(
                    PRIVACY_NOTICE,
                    SupportUtils.getMozillaPageUrl(SupportUtils.MozillaPage.PRIVACY_NOTICE),
                ),
                getString(R.string.about_privacy_notice),
            ),
            AboutPageItem(
                AboutItem.ExternalLink(
                    RIGHTS,
                    SupportUtils.getSumoURLForTopic(context, SupportUtils.SumoTopic.YOUR_RIGHTS),
                ),
                getString(R.string.about_know_your_rights),
            ),
        )
    }
    fun clicked(item: AboutItem) {
        when (item.type) {
                    WHATS_NEW -> {
                        WhatsNew.userViewedWhatsNew(requireContext())
                        Events.whatsNewTapped.record(Events.WhatsNewTappedExtra(source = "ABOUT"))
                    }
        }
    }
    companion object {
        private const val ABOUT_LICENSE_URL = "about:license"
    }
}'''


class OverlayTests(unittest.TestCase):
    def make_checkout(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "mach").write_text("#!/bin/sh\n")
        app = root / "mobile/android/fenix/app"
        (app / "src/main/res/values").mkdir(parents=True)
        (app / "src/main/res/values-night").mkdir(parents=True)
        (app / "src/main/res/values-es").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/utils").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/browser/desktopmode").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/onboarding").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/components").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/components/toolbar").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/settings/about").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/settings").mkdir(parents=True, exist_ok=True)
        (app / "src/main/java/org/mozilla/fenix/home/ui").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/components/menu/compose").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/tabstray/redux/middleware").mkdir(parents=True)
        (app / "src/main/java/org/mozilla/fenix/tabstray/ui").mkdir(parents=True)
        (app / "src/main/res/xml").mkdir(parents=True)
        (app / "src/release").mkdir(parents=True)
        (app / "src/beta").mkdir(parents=True)
        (app / "src/release/res/values").mkdir(parents=True)
        (app / "src/beta/res/values").mkdir(parents=True)
        (app / "build.gradle").write_text(GRADLE)
        (app / "src/main/AndroidManifest.xml").write_text(MANIFEST)
        (app / "src/release/AndroidManifest.xml").write_text(CHANNEL_MANIFEST)
        (app / "src/beta/AndroidManifest.xml").write_text(CHANNEL_MANIFEST)
        (app / "src/main/java/org/mozilla/fenix/utils/Settings.kt").write_text(SETTINGS)
        (app / "src/main/java/org/mozilla/fenix/onboarding/OnboardingFragment.kt").write_text(
            ONBOARDING)
        (app / "src/main/java/org/mozilla/fenix/components/SettingsSearchProviders.kt").write_text(
            SEARCH_PROVIDERS)
        (app / "src/main/java/org/mozilla/fenix/components/Core.kt").write_text(CORE)
        (app / "src/main/java/org/mozilla/fenix/HomeActivity.kt").write_text(HOME_ACTIVITY)
        (app / "src/main/java/org/mozilla/fenix/home/ui/Homepage.kt").write_text(HOMEPAGE)
        (app / "src/main/java/org/mozilla/fenix/components/menu/compose/MainMenu.kt").write_text(MAIN_MENU)
        (app / "src/main/java/org/mozilla/fenix/components/menu/MenuDialogFragment.kt").write_text(MENU_DIALOG)
        (app / "src/main/java/org/mozilla/fenix/components/menu/compose/MoreSettingsSubmenu.kt").write_text(
            MORE_SETTINGS
        )
        (app / "src/main/java/org/mozilla/fenix/tabstray/redux/middleware/TabStorageMiddleware.kt").write_text(
            TAB_STORAGE_MIDDLEWARE
        )
        (app / "src/main/java/org/mozilla/fenix/tabstray/ui/TabManagementFragment.kt").write_text(
            TAB_MANAGEMENT_FRAGMENT
        )
        (app / "src/main/java/org/mozilla/fenix/components/toolbar/BrowserToolbarComposable.kt").write_text(
            BROWSER_TOOLBAR)
        (app / "src/main/java/org/mozilla/fenix/browser").mkdir(parents=True, exist_ok=True)
        (app / "src/main/java/org/mozilla/fenix/browser/BaseBrowserFragment.kt").write_text(
            BASE_BROWSER_FRAGMENT)
        (app / "src/main/java/org/mozilla/fenix/browser/BrowserFragment.kt").write_text(
            BROWSER_FRAGMENT
        )
        (
            app
            / "src/main/java/org/mozilla/fenix/browser/NativeShareSheetContextMenuCandidate.kt"
        ).write_text(NATIVE_CONTEXT_MENU_CANDIDATES)
        context_menu = (
            root
            / "mobile/android/android-components/components/feature/contextmenu/src/main/java/mozilla/components/feature/contextmenu"
        )
        context_menu.mkdir(parents=True, exist_ok=True)
        (context_menu / "ContextMenuCandidate.kt").write_text(
            COMPONENT_CONTEXT_MENU_CANDIDATES
        )
        clipping_behavior = (
            root
            / "mobile/android/android-components/components/ui/widgets/src/main/java/mozilla/components/ui/widgets/behavior"
        )
        clipping_behavior.mkdir(parents=True, exist_ok=True)
        (clipping_behavior / "EngineViewClippingBehavior.kt").write_text(
            ENGINE_VIEW_CLIPPING_BEHAVIOR
        )
        toolbar_feature = (
            root
            / "mobile/android/android-components/components/feature/toolbar/src/main/java/mozilla/components/feature/toolbar"
        )
        toolbar_feature.mkdir(parents=True, exist_ok=True)
        (toolbar_feature / "ToolbarBehaviorController.kt").write_text(
            TOOLBAR_BEHAVIOR_CONTROLLER
        )
        compose_toolbar = (
            root
            / "mobile/android/android-components/components/compose/browser-toolbar/src/main/java/mozilla/components/compose/browser/toolbar"
        )
        (compose_toolbar / "ui").mkdir(parents=True)
        (compose_toolbar / "ui/FullDisplayToolbar.kt").write_text(FULL_DISPLAY_TOOLBAR)
        (compose_toolbar / "BrowserEditToolbar.kt").write_text(BROWSER_EDIT_TOOLBAR)
        (compose_toolbar / "BrowserToolbar.kt").write_text(COMPOSE_BROWSER_TOOLBAR)
        (app / "src/main/java/org/mozilla/fenix/settings/about/AboutFragment.kt").write_text(ABOUT)
        (app / "src/main/java/org/mozilla/fenix/settings/CustomizationFragment.kt").write_text(
            CUSTOMIZATION_FRAGMENT)
        (app / "src/main/java/org/mozilla/fenix/browser/desktopmode/DesktopModeRepository.kt").write_text(
            DESKTOP_MODE)
        (app / "src/main/java/org/mozilla/fenix/home/ui/Wordmark.kt").write_text(WORDMARK)
        (app / "src/main/res/values/colors.xml").write_text(COLORS)
        (app / "src/main/res/values-night/colors.xml").write_text(NIGHT_COLORS)
        (app / "src/main/res/values/styles.xml").write_text(STYLES)
        (app / "src/main/res/xml/customization_preferences.xml").write_text(CUSTOMIZATION)
        (app / "src/main/res/xml/preferences.xml").write_text(PREFERENCES)
        (app / "src/main/res/values/static_strings.xml").write_text(
            '<resources><string name="app_name">Firefox Fenix</string></resources>')
        (app / "src/release/res/values/static_strings.xml").write_text(
            '<resources><string name="app_name">Firefox</string></resources>')
        (app / "src/beta/res/values/static_strings.xml").write_text(
            '<resources><string name="app_name">Firefox Beta</string></resources>')
        (app / "src/main/res/values/strings.xml").write_text(
            '<resources>'
            '<string name="about_content">%1$s is produced by Mozilla.</string>'
            '<string name="welcome">Welcome to Mozilla Firefox</string>'
            '<string name="marketing">Tell a partner that you’re a Firefox user.</string>'
            '<string name="onboarding_term_of_service_line_one_link_text_2">Firefox Terms of Use</string>'
            '<string name="sync_connect_device_dialog">Sign in to Firefox on another device.</string>'
            + WORKSPACE_STRINGS +
            '</resources>')
        (app / "src/main/res/values-es/strings.xml").write_text(
            '<resources><string name="welcome">Bienvenido a Firefox</string></resources>')
        return temp, root

    def test_styles_display_and_edit_address_fields(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root, channel="beta")
        compose_toolbar = (
            root
            / "mobile/android/android-components/components/compose/browser-toolbar/src/main/java/mozilla/components/compose/browser/toolbar"
        )
        for source in (
            compose_toolbar / "ui/FullDisplayToolbar.kt",
            compose_toolbar / "BrowserEditToolbar.kt",
        ):
            text = source.read_text()
            self.assertIn("Brush.horizontalGradient", text)
            self.assertIn("Color(0xD034373C)", text)
            self.assertIn("Color(0x99F1F2F4)", text)
            self.assertIn("import androidx.compose.foundation.border", text)

    def test_opaque_toolbar_preference_is_persisted_and_rendered(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root, channel="beta")
        app = root / "mobile/android/fenix/app"
        settings = (app / "src/main/java/org/mozilla/fenix/utils/Settings.kt").read_text()
        preferences = (app / "src/main/res/xml/customization_preferences.xml").read_text()
        toolbar = (
            app / "src/main/java/org/mozilla/fenix/components/toolbar/BrowserToolbarComposable.kt"
        ).read_text()
        self.assertIn('"acute_reduce_transparency"', settings)
        self.assertIn('android:key="acute_reduce_transparency"', preferences)
        self.assertIn("LocalContext.current.settings().acuteReduceTransparency", toolbar)
        self.assertIn("Color(0xFF25282D)", toolbar)
        self.assertIn("Color(0xFF1B1D21)", toolbar)
        self.assertIn("Color(0xFF121417)", toolbar)
        self.assertEqual(toolbar.count("import androidx.compose.ui.platform.LocalContext"), 1)

    def test_composites_toolbar_over_live_gecko_content(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root, channel="beta")
        compose_toolbar = (
            root
            / "mobile/android/android-components/components/compose/browser-toolbar/src/main/java/mozilla/components/compose/browser/toolbar/BrowserToolbar.kt"
        ).read_text()
        browser_fragment = (
            root
            / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix/browser/BaseBrowserFragment.kt"
        ).read_text()
        clipping_behavior = (
            root
            / "mobile/android/android-components/components/ui/widgets/src/main/java/mozilla/components/ui/widgets/behavior/EngineViewClippingBehavior.kt"
        ).read_text()
        toolbar_behavior = (
            root
            / "mobile/android/android-components/components/feature/toolbar/src/main/java/mozilla/components/feature/toolbar/ToolbarBehaviorController.kt"
        ).read_text()
        self.assertIn("val backgroundColor = Color.Transparent", compose_toolbar)
        self.assertIn("val acuteGlassTopOverlayHeight = 0", browser_fragment)
        self.assertIn("import org.mozilla.fenix.utils.isLargeScreenSize", browser_fragment)
        self.assertIn("!context.isLargeScreenSize()", browser_fragment)
        self.assertIn(
            "setDynamicToolbarMaxHeight(bottomToolbarHeight)",
            browser_fragment,
        )
        self.assertNotIn(
            "setDynamicToolbarMaxHeight(topToolbarHeight + bottomToolbarHeight)",
            browser_fragment,
        )
        self.assertIn("topToolbarHeight = topToolbarHeight", browser_fragment)
        self.assertIn(
            "if (context.isLargeScreenSize()) topToolbarHeight else acuteGlassTopOverlayHeight",
            browser_fragment,
        )
        self.assertIn("engineViewParent.translationY = 0f", clipping_behavior)
        self.assertIn("dynamicToolbarMaxHeight = bottomToolbarHeight", clipping_behavior)
        self.assertIn(
            "contentBottomClipping = (-recentBottomToolbarTranslation).roundToInt()",
            clipping_behavior,
        )
        self.assertNotIn(
            "recentTopToolbarTranslation - recentBottomToolbarTranslation",
            clipping_behavior,
        )
        self.assertIn("toolbar.collapse()", toolbar_behavior)

    def test_site_display_is_available_in_both_channels(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root, channel="beta")
        app = root / "mobile/android/fenix/app"
        core = (app / "src/main/java/org/mozilla/fenix/components/Core.kt").read_text()
        self.assertIn("midnight-pages@acuteweb.core", core)
        self.assertIn("saved-sessions@acuteweb.core", core)
        self.assertIn("page-notes@acuteweb.core", core)
        self.assertTrue(
            (app / "src/main/assets/extensions/acute-midnight/manifest.json").is_file()
        )
        self.assertTrue(
            (app / "src/main/assets/extensions/acute-midnight/midnight.js").is_file()
        )
        self.assertTrue(
            (app / "src/main/assets/extensions/acute-midnight/popup.html").is_file()
        )

        stable_temp, stable_root = self.make_checkout()
        self.addCleanup(stable_temp.cleanup)
        apply(stable_root, channel="stable")
        stable_core = (
            stable_root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix/components/Core.kt"
        ).read_text()
        self.assertIn("midnight-pages@acuteweb.core", stable_core)
        self.assertIn("saved-sessions@acuteweb.core", stable_core)
        self.assertIn("page-notes@acuteweb.core", stable_core)
        self.assertTrue(
            (
                stable_root
                / "mobile/android/fenix/app/src/main/assets/extensions/acute-sessions/manifest.json"
            ).is_file()
        )
        self.assertTrue(
            (
                stable_root
                / "mobile/android/fenix/app/src/main/assets/extensions/acute-notes/manifest.json"
            ).is_file()
        )

    def test_adds_clean_link_action_and_prioritizes_sharing(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root, channel="beta")
        app = root / "mobile/android/fenix/app"
        browser = (
            app / "src/main/java/org/mozilla/fenix/browser/BrowserFragment.kt"
        ).read_text()
        native = (
            app
            / "src/main/java/org/mozilla/fenix/browser/NativeShareSheetContextMenuCandidate.kt"
        ).read_text()
        component = (
            root
            / "mobile/android/android-components/components/feature/contextmenu/src/main/java/mozilla/components/feature/contextmenu/ContextMenuCandidate.kt"
        ).read_text()
        context_strings = (
            app / "src/main/res/values/acute_context_menu_strings.xml"
        ).read_text()

        self.assertIn('id = "acute.contextmenu.copy_clean_link"', browser)
        self.assertIn("cleanTrackingUrl(hitResult.getUrl())", browser)
        self.assertIn('name.startsWith("utm_")', browser)
        self.assertIn('"fbclid"', browser)
        self.assertIn("append(fragment)", browser)
        self.assertIn("Copy clean link", context_strings)
        self.assertLess(
            native.index("createShareLinkCandidate("),
            native.index("createDownloadLinkCandidate("),
        )
        self.assertLess(
            component.index("createShareLinkCandidate(context)"),
            component.index("createDownloadLinkCandidate("),
        )

    def test_applies_branding_privacy_updater_and_signing(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root)
        app = root / "mobile/android/fenix/app"
        gradle = (app / "build.gradle").read_text()
        manifest = (app / "src/main/AndroidManifest.xml").read_text()
        strings = (app / "src/main/res/values/strings.xml").read_text()
        static_strings = (app / "src/main/res/values/static_strings.xml").read_text()
        self.assertIn('applicationId "com.acuteweb.browser"', gradle)
        self.assertIn('applicationIdSuffix ".beta"', gradle)
        self.assertNotIn("org.mozilla.firefox.sharedID", gradle)
        self.assertNotIn("sharedUserId", (app / "src/release/AndroidManifest.xml").read_text())
        self.assertNotIn("'TELEMETRY', 'true'", gradle)
        self.assertNotIn("ACUTE_KEYSTORE_PATH", gradle)
        self.assertIn("ACUTE_VERSION_NAME", gradle)
        self.assertIn("GitHubUpdateProvider", manifest)
        self.assertIn("android.hardware.touchscreen", manifest)
        self.assertNotIn("com.adjust.preinstall.READ_PERMISSION", manifest)
        self.assertNotIn("com.google.android.gms.permission.AD_ID", manifest)
        self.assertNotIn("android.permission.QUERY_ALL_PACKAGES", manifest)
        self.assertNotIn("android.permission.REQUEST_DELETE_PACKAGES", manifest)
        self.assertNotIn("android.permission.REQUEST_INSTALL_PACKAGES", manifest)
        tablet_settings = (app / "src/main/java/org/mozilla/fenix/utils/Settings.kt").read_text()
        self.assertIn("Acute Web: tablets always start with the top tab strip", tablet_settings)
        self.assertIn("appContext.isLargeScreenSize()", tablet_settings)
        self.assertIn("isMarketingTelemetryEnabled: Boolean", tablet_settings)
        self.assertIn("get() = false", tablet_settings)
        self.assertIn("crashReportChoice: String", tablet_settings)
        self.assertIn("CrashReportOption.Never", tablet_settings)
        self.assertIn("one application theme: Midnight", tablet_settings)
        self.assertIn("shouldUseDarkTheme: Boolean", tablet_settings)
        self.assertIn("get() = true", tablet_settings)
        self.assertIn("shouldUseLightTheme: Boolean", tablet_settings)
        self.assertIn("shouldFollowDeviceTheme: Boolean", tablet_settings)
        night_colors = (app / "src/main/res/values-night/colors.xml").read_text()
        self.assertIn(
            '<color name="fx_mobile_primary">@color/acute_glass_light</color>',
            night_colors,
        )
        self.assertIn(
            '<color name="fx_mobile_surface">@color/acute_glass_surface</color>',
            night_colors,
        )
        toolbar = (
            app / "src/main/java/org/mozilla/fenix/components/toolbar/BrowserToolbarComposable.kt"
        ).read_text()
        self.assertIn("acuteCoreGlassModifier", toolbar)
        self.assertIn("Brush.verticalGradient", toolbar)
        self.assertIn("LocalConfiguration.current.smallestScreenWidthDp >= 600", toolbar)
        self.assertIn("Color(0xE025282D)", toolbar)
        self.assertIn("Color(0x66F1F2F4)", toolbar)
        self.assertEqual(toolbar.count("Column(modifier = acuteCoreGlassModifier)"), 2)
        customization = (app / "src/main/res/xml/customization_preferences.xml").read_text()
        self.assertNotIn("preferences_theme", customization)
        self.assertNotIn("pref_key_light_theme", customization)
        fragment = (app / "src/main/java/org/mozilla/fenix/settings/CustomizationFragment.kt").read_text()
        self.assertNotIn("bindLightTheme()", fragment)
        self.assertIn("permanently rendered with the Midnight theme", fragment)
        self.assertIn("showPocketRecommendationsFeature: Boolean", tablet_settings)
        self.assertIn("showContileFeature: Boolean", tablet_settings)
        self.assertIn("Acute Workspaces is a first-class, local dashboard feature", tablet_settings)
        self.assertIn("Keep the contextual Add to workspace command discoverable", tablet_settings)
        self.assertEqual(tablet_settings.count("default = { true }"), 2)
        home_activity = (app / "src/main/java/org/mozilla/fenix/HomeActivity.kt").read_text()
        self.assertIn("handleAcuteDesktopShortcut", home_activity)
        self.assertIn("isLargeScreenSize()", home_activity)
        self.assertIn("KeyEvent.KEYCODE_L", home_activity)
        self.assertIn("KeyEvent.KEYCODE_T", home_activity)
        self.assertIn("KeyEvent.KEYCODE_W", home_activity)
        self.assertIn("KeyEvent.KEYCODE_TAB", home_activity)
        self.assertIn("KeyEvent.KEYCODE_R", home_activity)
        self.assertIn("KeyEvent.KEYCODE_F5", home_activity)
        self.assertIn("KeyEvent.KEYCODE_F6", home_activity)
        self.assertIn("tabsUseCases.undo()", home_activity)
        self.assertIn("sessionUseCases.goBack()", home_activity)
        self.assertIn("sessionUseCases.goForward()", home_activity)
        self.assertIn("dispatchGenericMotionEvent", home_activity)
        self.assertIn("MotionEvent.BUTTON_BACK", home_activity)
        self.assertIn("MotionEvent.BUTTON_FORWARD", home_activity)
        homepage = (app / "src/main/java/org/mozilla/fenix/home/ui/Homepage.kt").read_text()
        self.assertIn("Acute owns the homepage hierarchy", homepage)
        self.assertIn("Acute's dashboard begins with user-owned shortcuts", homepage)
        self.assertIn("reducedTopSpacing = false", homepage)
        self.assertIn("emptyList<PopularSite>()", homepage)
        self.assertNotIn("ExperimentalHomepageHeader(", homepage)
        self.assertNotIn("PocketSection(", homepage)
        self.assertNotIn("observePopularSites(topSites =", homepage)
        self.assertNotIn("trackersBlockedCount = trackersBlockedCount", homepage)
        self.assertIn("val acuteExpandedDashboard = maxWidth >= 840.dp", homepage)
        self.assertIn(
            "acuteExpandedDashboard && (bookmarks != null || recentlyVisited != null)",
            homepage,
        )
        self.assertIn("Row(modifier = Modifier.fillMaxWidth())", homepage)
        self.assertEqual(homepage.count("Column(modifier = Modifier.weight(1f))"), 1)
        self.assertEqual(homepage.count("Box(modifier = Modifier.weight(1f))"), 1)
        self.assertIn("import androidx.compose.foundation.layout.Row", homepage)
        self.assertIn("import androidx.compose.foundation.layout.fillMaxWidth", homepage)
        self.assertIn("Acute Workspaces is backed by the maintained local tab-group store", homepage)
        self.assertIn("CollectionsMigrationPromoCard(", homepage)
        self.assertNotIn("is CollectionsState.Content ->", homepage)
        main_menu = (
            app / "src/main/java/org/mozilla/fenix/components/menu/compose/MainMenu.kt"
        ).read_text()
        menu_dialog = (
            app / "src/main/java/org/mozilla/fenix/components/menu/MenuDialogFragment.kt"
        ).read_text()
        more_settings = (
            app
            / "src/main/java/org/mozilla/fenix/components/menu/compose/MoreSettingsSubmenu.kt"
        ).read_text()
        self.assertIn("fixed library actions never move", main_menu)
        self.assertLess(main_menu.index("LibraryMenuGroup("), main_menu.index("ToolsAndActionsMenuGroup("))
        self.assertNotIn("MenuBanner(", main_menu)
        self.assertNotIn("IPProtectionMenuItem(", main_menu)
        self.assertNotIn("MozillaAccountMenuItem(", main_menu)
        self.assertIn("visible = !context.isLargeScreenSize()", menu_dialog)
        self.assertIn("MaterialTheme.shapes.extraLarge", menu_dialog)
        self.assertIn("dependable document capture one tap away", main_menu)
        self.assertIn("R.string.browser_menu_save_as_pdf_2", main_menu)
        self.assertIn("R.string.browser_menu_print_2", main_menu)
        self.assertIn("saveToPdfUseCase()", menu_dialog)
        self.assertIn("printContentUseCase()", menu_dialog)
        self.assertIn("showCaptureActions = false", menu_dialog)
        self.assertIn("if (showCaptureActions)", more_settings)
        self.assertNotIn("showPocketRecommendationsFeature by", tablet_settings)
        self.assertNotIn("showContileFeature by", tablet_settings)
        styles = (app / "src/main/res/values/styles.xml").read_text()
        self.assertNotIn("ic_logo_wordmark", styles)
        self.assertNotIn("ic_wordmark_logo", styles)
        self.assertIn("@drawable/acute_brand_mark", styles)
        about = (app / "src/main/java/org/mozilla/fenix/settings/about/AboutFragment.kt").read_text()
        self.assertIn("ACUTE_RELEASES_URL", about)
        self.assertIn("ACUTE_ISSUES_URL", about)
        self.assertIn("ACUTE_PRIVACY_URL", about)
        self.assertNotIn("SupportUtils.WHATS_NEW_URL", about)
        self.assertNotIn("AboutItem.Crashes", about)
        self.assertIn('"${packageInfo.versionName} (Build #$versionCode)"', about)
        self.assertNotIn("GeckoViewBuildConfig", about)
        self.assertNotIn("VCS_HASH", about)
        self.assertIn("binding.buildDate.visibility = View.GONE", about)
        onboarding = (app / "src/main/java/org/mozilla/fenix/onboarding/OnboardingFragment.kt").read_text()
        self.assertIn("never displays Mozilla marketing", onboarding)
        self.assertNotIn("MarketingPageAdditionSupport(", onboarding)
        preferences = (app / "src/main/res/xml/preferences.xml").read_text()
        self.assertIn('android:key="acute_report_issue"', preferences)
        self.assertNotIn("pref_key_data_choices", preferences)
        providers = (app / "src/main/java/org/mozilla/fenix/components/SettingsSearchProviders.kt").read_text()
        self.assertNotIn("DataChoicesSearchProvider", providers)
        reporting_strings = (app / "src/main/res/values/acute_reporting_strings.xml").read_text()
        self.assertIn("issues/new/choose", reporting_strings)
        self.assertIn("Welcome to Acute Web", strings)
        self.assertIn('name="create_tab_group_title">Create workspace<', strings)
        self.assertIn('name="collections_migration_homepage_banner_title">Workspaces<', strings)
        self.assertIn("%1$d workspaces open. Tap to switch tabs.", strings)
        self.assertIn("Dissolve workspace?", strings)
        self.assertIn('name="tab_group_three_dot_menu_close">Suspend<', strings)
        tab_storage_middleware = (
            app / "src/main/java/org/mozilla/fenix/tabstray/redux/middleware/TabStorageMiddleware.kt"
        ).read_text()
        tab_management_fragment = (
            app / "src/main/java/org/mozilla/fenix/tabstray/ui/TabManagementFragment.kt"
        ).read_text()
        self.assertIn("private val suspendTab: (String) -> Unit = {}", tab_storage_middleware)
        self.assertIn("action.group.tabs.forEach { tab -> suspendTab(tab.id) }", tab_storage_middleware)
        self.assertLess(
            tab_storage_middleware.index("suspendTab(tab.id)"),
            tab_storage_middleware.index("tabGroupRepository.closeTabGroup"),
        )
        self.assertIn("EngineAction.SuspendEngineSessionAction(tabId)", tab_management_fragment)
        self.assertIn("you’re an Acute Web user", strings)
        self.assertIn("developed by CORE using Mozilla’s open-source Gecko engine", strings)
        self.assertIn("Firefox Terms of Use", strings)
        self.assertIn("Sign in to Firefox on another device", strings)
        self.assertIn(
            "Bienvenido a Acute Web",
            (app / "src/main/res/values-es/strings.xml").read_text(),
        )
        self.assertIn('name="app_name">Acute Web<', static_strings)
        self.assertIn(
            'name="app_name">Acute Web<',
            (app / "src/release/res/values/static_strings.xml").read_text(),
        )
        self.assertIn(
            'name="app_name">Acute Web<',
            (app / "src/beta/res/values/static_strings.xml").read_text(),
        )
        self.assertTrue((app / "src/main/java/org/mozilla/fenix/acute/GitHubUpdateProvider.kt").is_file())
        self.assertTrue((root / ".acute-web-android-overlay").is_file())

    def test_product_identity_gate_scans_static_integration_strings(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        values = root / "mobile/android/fenix/app/src/main/res/values"
        static_strings = values / "static_strings.xml"
        static_strings.write_text(
            '<resources><string name="widget_promo">Add Firefox widget</string></resources>'
        )
        with self.assertRaises(OverlayError):
            apply(root, channel="beta")

    def test_product_branding_removes_disabled_upstream_service_copy(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        strings = root / "mobile/android/fenix/app/src/main/res/values/strings.xml"
        strings.write_text(
            "<resources>"
            '<string name="preferences_rate">Rate on Google Play</string>'
            '<string name="preferences_show_sponsored_suggestions_summary">Sponsored suggestions</string>'
            '<string name="customize_toggle_contile">Sponsored shortcuts</string>'
            '<string name="pair_instructions_2">Visit firefox.com/pair</string>'
            '<string name="sign_in_instructions">Visit firefox.com/pair</string>'
            '<string name="about_content">Firefox</string>'
            + WORKSPACE_STRINGS +
            "</resources>"
        )
        apply(root, channel="beta")
        branded = strings.read_text()
        self.assertIn("Visit the Acute Web project", branded)
        self.assertIn("Recommendations are disabled in Acute Web", branded)
        self.assertIn("Sync pairing is not available in Acute Web", branded)
        self.assertNotIn("Google Play", branded)
        self.assertNotIn("Sponsored", branded)
        self.assertNotIn("firefox.com/pair", branded)

    def test_product_identity_gate_rejects_upstream_promotions(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        source = root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix"
        source.mkdir(parents=True, exist_ok=True)
        (source / "UpstreamPromotion.kt").write_text(
            'val promotion = "Try Mozilla VPN"'
        )
        with self.assertRaises(OverlayError):
            apply(root, channel="beta")

    def test_product_identity_gate_rejects_runtime_ui_branding(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        source = root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix"
        source.mkdir(parents=True, exist_ok=True)
        (source / "RuntimePrompt.kt").write_text(
            'val prompt = "Try the Firefox search widget"'
        )
        with self.assertRaises(OverlayError):
            apply(root, channel="beta")

    def test_product_identity_gate_ignores_internal_upstream_references(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        source = root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix"
        source.mkdir(parents=True, exist_ok=True)
        (source / "InternalFeature.kt").write_text(
            "// Pocket recommendations are disabled by Acute\n"
            "val firefoxSuggestEnabled = false"
        )
        apply(root, channel="beta")

    def test_product_identity_gate_ignores_quoted_names_in_comments(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        source = root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix"
        source.mkdir(parents=True, exist_ok=True)
        (source / "DocumentedFeature.kt").write_text(
            '/** "Firefox Suggest" header. */\n'
            '// "Sponsored suggestions" are disabled by Acute.\n'
            'val enabled = false'
        )
        apply(root, channel="beta")

    def test_product_identity_gate_rejects_hardcoded_upstream_promotions(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        source = root / "mobile/android/fenix/app/src/main/java/org/mozilla/fenix"
        source.mkdir(parents=True, exist_ok=True)
        (source / "UpstreamOnboardingPromotion.kt").write_text(
            'val promotion = "Pocket recommendations"'
        )
        with self.assertRaises(OverlayError):
            apply(root, channel="beta")

    def test_beta_channel_has_separate_identity(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root, channel="beta")
        app = root / "mobile/android/fenix/app"
        self.assertIn(
            'name="app_name">Acute Beta<',
            (app / "src/beta/res/values/static_strings.xml").read_text(),
        )
        self.assertIn(
            'name="app_name">Acute Web<',
            (app / "src/release/res/values/static_strings.xml").read_text(),
        )
        self.assertEqual(
            (root / ".acute-web-android-overlay").read_text(),
            "Acute Web Android overlay applied (beta)\n",
        )
        beta_icon = (app / "src/beta/res/mipmap-anydpi-v33/ic_launcher.xml").read_text()
        self.assertIn("@drawable/acute_beta_launcher_foreground", beta_icon)
        self.assertIn("@drawable/acute_beta_launcher_monochrome", beta_icon)
        stable_icon = (app / "src/release/res/mipmap-anydpi-v33/ic_launcher.xml").read_text()
        self.assertNotIn("acute_beta", stable_icon)

    def test_rejects_unknown_channel(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        with self.assertRaises(OverlayError):
            apply(root, channel="nightly")

    def test_refuses_second_application(self):
        temp, root = self.make_checkout()
        self.addCleanup(temp.cleanup)
        apply(root)
        with self.assertRaises(OverlayError):
            apply(root)

    def test_requires_firefox_checkout(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(OverlayError):
                apply(Path(name))


if __name__ == "__main__":
    unittest.main()
