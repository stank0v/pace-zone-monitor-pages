# Road Monitor — pages

Support and privacy pages for the **Road Monitor** iOS app,
served via GitHub Pages.

| Page | URL |
|---|---|
| Home | `https://stank0v.github.io/pace-zone-monitor-pages/` |
| Support | `https://stank0v.github.io/pace-zone-monitor-pages/support.html` |
| Privacy Policy | `https://stank0v.github.io/pace-zone-monitor-pages/privacy.html` |

The Bulgarian site (home, `sredna-skorost/` — a page per road and per
average-speed zone — and the `vodach/` guides) is generated from the app's zone
catalog; `sitemap.xml` and `robots.txt` too:

    python3 tools/build.py --catalog ~/Development/SpeedCam/SpeedCam

Rebuild after every catalog change. `privacy.html`, `support.html` and the
English landing page `en/` are hand-written. `site.css` + `fonts/` (Onest,
OFL) style the generated pages; `style.css` the hand-written ones.

Static HTML, no runtime dependencies (maps load Leaflet + OpenStreetMap tiles). `.nojekyll` disables Jekyll
processing so the files are served exactly as committed.

## App Store Connect

- **Support URL** → the support page above
- **Privacy Policy URL** → the privacy page above

## Keeping it accurate

The privacy policy states that the developer does not collect trip or location
data. It also explains that Apple provides map and purchase services. Keep
`privacy.html` aligned with the released app.
