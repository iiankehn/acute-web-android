# Acute artwork

Illustrations that replace Firefox's fox and Kit mascot art. Put a transparent
PNG here with the exact file name below and the next build uses it. Any image
that isn't here is shown as the Acute mark instead.

Make each image about 4× the listed size, in the same proportions
(for example, 248 × 252 px for a 62 × 63 dp image).

| File | Where it appears | Size (dp) |
|---|---|---|
| `fox_ai_on_state.png` | Settings › AI controls banner | 62 × 63 |
| `kit_sleeping_under_laptop.png` | Settings › Acute Web Labs, when no features are available | 180 × 103 |
| `kit_expressive_full.png` | Settings › Acute Web Labs banner | 66 × 62 |
| `fox_exclamation_alert.png` | Settings search and tab search, no results | 200 × 200 |
| `illustration_fox_box_inside_light.png` | Downloads, empty list | 176 × 160 |
| `ic_kit_bookmarks_empty_state.png` | Bookmarks, empty list | 200 × 178 |
| `kit_search_error.png` | Bookmarks search, no results | 120 × 139 |
| `kit_head_protection_blocker_banner.png` | Site protection panel banner | 78 × 78 |
| `ic_kit_plug_error.png` | Screen shown after a crash at startup | 200 × 150 |
| `kit_devices_sync.png` | Send tab to device | 210 × 90 |
| `kit_devices_sync_error.png` | Send tab to device, sync error | 242 × 90 |
| `kit_plug_error.png` | Send tab to device, offline | 137 × 103 |
| `ic_kit_heart.png` | Onboarding variant (normally hidden) | 141 × 150 |
| `ic_kit_shield_on_state.png` | VPN feature (normally hidden) | 58 × 60 |
| `ic_kit_shield_off_state.png` | VPN feature (normally hidden) | 58 × 60 |
| `firefox_as_default_banner_illustration.png` | Menu banner (normally hidden) | 78 × 53 |

## Page states

Error pages and the crashed-tab screen. These six are required; the build
fails if one is missing. They are shown up to 320 dp wide.

| File | Shown for |
|---|---|
| `acute_connection_failed.png` | Connection reset, interrupted or timed out; unknown proxy; any error without its own image |
| `acute_page_not_found.png` | Address not found, connection refused, malformed address, file not found |
| `acute_not_encrypted.png` | HTTPS-Only warning (site doesn't support HTTPS) |
| `acute_certificate_error.png` | Certificate and secure-connection errors, blocked port |
| `acute_offline.png` | No internet connection |
| `acute_tab_crashed.png` | Crashed tab screen; corrupted or unsafe content; redirect loop |
