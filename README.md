# Pace Zone Monitor — pages

Support and privacy pages for the **Pace Zone Monitor** iOS app,
served via GitHub Pages.

| Page | URL |
|---|---|
| Home | `https://stank0v.github.io/pace-zone-monitor-pages/` |
| Support | `https://stank0v.github.io/pace-zone-monitor-pages/support.html` |
| Privacy Policy | `https://stank0v.github.io/pace-zone-monitor-pages/privacy.html` |

Static HTML, no build step, no dependencies. `.nojekyll` disables Jekyll
processing so the files are served exactly as committed.

## App Store Connect

- **Support URL** → the support page above
- **Privacy Policy URL** → the privacy page above

## Keeping it accurate

The privacy policy states that the app collects nothing, transmits nothing,
and uses location only on-device. If the app's behaviour ever changes —
analytics, crash reporting, accounts, or anything that sends data off the
device — `privacy.html` must be updated **before** that version ships.
