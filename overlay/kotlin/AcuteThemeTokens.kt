package org.mozilla.fenix.acute

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.material3.ColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import mozilla.components.compose.base.theme.AcornColors
import mozilla.components.compose.base.theme.AcornGradient
import mozilla.components.compose.base.theme.AcornGradientScheme
import mozilla.components.compose.base.theme.AcornGradientType
import mozilla.components.compose.base.theme.acornDarkColorScheme
import mozilla.components.compose.base.theme.darkColorPalette
import mozilla.components.compose.base.utils.ColorStop
import org.mozilla.fenix.ext.components

/** Acute owns structural colors; upstream retains semantic error/success/warning roles. */
object AcuteThemeTokens {
    val canvas = Color(0xFF08090B)
    val surface = Color(0xFF191B1F)
    val raised = Color(0xFF25282D)
    val selected = Color(0xFF33363C)
    val text = Color(0xFFF4F5F6)
    val muted = Color(0xFFB9BDC3)
    val light = Color(0xFFF1F2F4)
    val outline = Color(0xFF8E9299)

    fun colorScheme(isPrivate: Boolean): ColorScheme = acornDarkColorScheme().copy(
        primary = light, onPrimary = canvas,
        primaryContainer = selected, onPrimaryContainer = text, inversePrimary = raised,
        secondary = muted, onSecondary = canvas,
        secondaryContainer = raised, onSecondaryContainer = text,
        tertiary = light, onTertiary = canvas,
        tertiaryContainer = selected, onTertiaryContainer = text,
        background = canvas, onBackground = text,
        surface = if (isPrivate) Color(0xFF202329) else surface, onSurface = text,
        surfaceVariant = raised, onSurfaceVariant = muted, surfaceTint = Color.Transparent,
        inverseSurface = text, inverseOnSurface = canvas,
        outline = outline, outlineVariant = Color(0xFF4D5158), scrim = Color(0x99000000),
        surfaceBright = raised, surfaceDim = canvas,
        surfaceContainer = surface, surfaceContainerHigh = raised,
        surfaceContainerHighest = selected, surfaceContainerLow = Color(0xFF111316),
        surfaceContainerLowest = canvas,
    )

    val colors: AcornColors = darkColorPalette.copy(
        formDefault = muted,
        information = light, onInformation = canvas,
        informationContainer = raised, onInformationContainer = text,
        surfaceDimVariant = canvas, surfaceContainerSelected = selected,
        autofillText = Color(0x668E9299), selectedText = Color(0x808E9299),
        iconPrivate = light, sheetOutline = Color(0xFF4D5158),
    )

    private fun gradient(start: Color, end: Color) = AcornGradient(
        type = AcornGradientType.Vertical,
        colorStops = listOf(ColorStop(0f, start), ColorStop(1f, end)),
    )

    val gradients = AcornGradientScheme(
        cfr = gradient(raised, surface),
        accent = gradient(selected, raised),
        accentSubtle = gradient(Color(0xD025282D), Color(0xC0191B1F)),
        tabOutline = gradient(light, outline),
        privacyMask = gradient(muted, light),
    )
}

/** Shared by browser and homepage chrome, including the accessibility override. */
@Composable
fun coreGlassToolbarModifier(): Modifier {
    val acuteLargeScreen = LocalConfiguration.current.smallestScreenWidthDp >= 600
    val acuteGlassColors =
        if (LocalContext.current.components.settings.acuteReduceTransparency) {
            listOf(Color(0xFF25282D), Color(0xFF1B1D21), Color(0xFF121417))
        } else if (acuteLargeScreen) {
            listOf(Color(0xE025282D), Color(0xD01B1D21), Color(0xC0121417))
        } else {
            listOf(Color(0xB316181C), Color(0xA60F1114), Color(0x99090B0D))
        }
    return Modifier.fillMaxWidth().wrapContentHeight()
        .background(Brush.verticalGradient(colors = acuteGlassColors))
        .drawWithContent {
            drawContent()
            drawLine(
                color = Color(0x66F1F2F4),
                start = Offset(0f, size.height - 1f),
                end = Offset(size.width, size.height - 1f),
                strokeWidth = 1f,
            )
        }
}
