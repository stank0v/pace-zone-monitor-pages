#!/usr/bin/env python3
"""Builds the Bulgarian Road Monitor site: the home page, a page per road with
average-speed control and a page per zone, the guides, sitemap.xml and
robots.txt. Every page is static HTML, written into the repository root, which
GitHub Pages serves as it is.

    python3 tools/build.py [--catalog ~/Development/SpeedCam/SpeedCam]
                           [--base https://stank0v.github.io/pace-zone-monitor-pages]

The zones come from the app's own catalog (segments_bg.json and
segment_routes.json), so the site says what the app measures. Rebuild after
every catalog change. privacy.html and support.html are hand-written and left
alone; the English landing page lives in en/.
"""
import argparse
import datetime
import html
import json
import math
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_ID = "6757105435"
APP_URL = f"https://apps.apple.com/bg/app/id{APP_ID}"
BG_TOLL = "https://www.bgtoll.bg"
MVR = "https://e-uslugi.mvr.bg"
BTA_38000 = "https://www.bta.bg/bg/news/983672-za-mesets-sa-zasecheni-blizo-38-000-narusheniya-zasneti-ot-tol-kameri"

TRANSLIT = dict(zip(
    "абвгдежзийклмнопрстуфхцчшщъьюя",
    ["a", "b", "v", "g", "d", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s",
     "t", "u", "f", "h", "ts", "ch", "sh", "sht", "a", "y", "yu", "ya"]))


def slug(text):
    text = "".join(TRANSLIT.get(c, c) for c in text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def esc(text):
    return html.escape(str(text), quote=True)


# MARK: - Data

class Road:
    def __init__(self, name):
        self.name = name
        self.zones = []

    @property
    def short(self):
        """АМ "Тракия" → Тракия; I-5 → I-5."""
        m = re.search(r'"([^"]+)"', self.name)
        return m.group(1) if m else self.name

    @property
    def display(self):
        """АМ „Тракия“, typographic quotes."""
        return re.sub(r'"([^"]+)"', r"„\1“", self.name)

    @property
    def is_motorway(self):
        return self.name.startswith("АМ")

    @property
    def slug(self):
        if self.is_motorway:
            return "am-" + slug(self.short)
        return slug(self.name)

    @property
    def kind(self):
        if self.is_motorway:
            return "автомагистрала"
        return "път " + ("I" if self.name.startswith("I-") else "II") + " клас"

    @property
    def length_km(self):
        return sum(z["approxLengthM"] for z in self.zones) / 1000


def load(catalog):
    segments = json.loads((catalog / "segments_bg.json").read_text())
    routes = json.loads((catalog / "segment_routes.json").read_text())
    roads = {}
    by_name = {s["name"]: s for s in segments}
    for s in segments:
        s["route"] = routes.get(s["id"]) or s.get("roadCoordinates") or [
            [s["start"]["lat"], s["start"]["lon"]], [s["end"]["lat"], s["end"]["lon"]]]
        a, _, b = s["name"].partition(" → ")
        s["reverse"] = by_name.get(f"{b} → {a}")
        s["from"], s["to"] = a, b
        roads.setdefault(s["road"], Road(s["road"])).zones.append(s)
    for road in roads.values():
        road.zones.sort(key=lambda z: (km(z["startKm"]) if z["startKm"] else 0, z["name"]))
    # Motorways first, then by how much of the road is covered.
    return sorted(roads.values(), key=lambda r: (not r.is_motorway, -len(r.zones)))


def km(marker):
    """'24+288' → 24.288."""
    if not marker:
        return 0.0
    whole, _, metres = marker.partition("+")
    return int(whole) + int(metres or 0) / 1000


def zone_slug(z):
    return slug(z["name"].replace("→", " "))


def zone_path(road, z):
    return f"sredna-skorost/{road.slug}/{zone_slug(z)}/"


def fmt_km(metres):
    return f"{metres / 1000:.1f}".replace(".", ",")


def fmt_duration(seconds):
    seconds = int(math.ceil(seconds))
    m, s = divmod(seconds, 60)
    return f"{m} мин {s:02d} с" if m else f"{s} с"


# MARK: - Page shell

CSS_VERSION = "2"


def page(base, path, title, description, body, *, schema=None, crumbs=None, map_data=None,
         en_alternate=False):
    canonical = f"{base}/{path}"
    depth = path.count("/")
    up = "../" * depth
    ld = []
    if schema:
        ld.extend(schema if isinstance(schema, list) else [schema])
    if crumbs:
        ld.append({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": name, "item": f"{base}/{p}"}
                for i, (name, p) in enumerate(crumbs)]})
    head_ld = "".join(
        f'\n<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    alternates = ""
    if en_alternate:
        alternates = (f'\n<link rel="alternate" hreflang="bg" href="{base}/">'
                      f'\n<link rel="alternate" hreflang="en" href="{base}/en/">'
                      f'\n<link rel="alternate" hreflang="x-default" href="{base}/">')
    crumb_html = ""
    if crumbs and len(crumbs) > 1:
        parts = [f'<a href="{up}{p}">{esc(n)}</a>' for n, p in crumbs[:-1]]
        crumb_html = f'<nav class="crumbs" aria-label="Навигация">{" › ".join(parts)}</nav>'
    map_html = ""
    if map_data:
        map_html = (
            f'\n<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" '
            f'integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">'
            f'\n<script defer src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" '
            f'integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>'
            f'\n<script defer src="{up}map.js?v={CSS_VERSION}"></script>'
            f'\n<script type="application/json" id="map-data">{json.dumps(map_data, ensure_ascii=False, separators=(",", ":"))}</script>')
    return f"""<!doctype html>
<html lang="bg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">{alternates}
<meta name="apple-itunes-app" content="app-id={APP_ID}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{base}/icon.png">
<meta property="og:locale" content="bg_BG">
<meta name="theme-color" content="#1B2430">
<link rel="icon" href="{up}favicon.png">
<link rel="preload" href="{up}fonts/Onest-ExtraBold.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{up}site.css?v={CSS_VERSION}">{head_ld}{map_html}
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="{up}"><img src="{up}icon-64.png" alt="" width="32" height="32">Road Monitor</a>
  <nav><a href="{up}sredna-skorost/">Средна скорост</a><a href="{up}vodach/">Наръчник</a><a href="{up}support.html" lang="en">Support</a></nav>
</div></header>
<main class="wrap">
{crumb_html}
{body}
</main>
<footer class="site"><div class="wrap">
  <p><a class="store" href="{APP_URL}">Изтегли Road Monitor от App Store</a></p>
  <p>Данните за отсечките са от каталога, който ползва приложението, по списъка на сертифицираните участъци на <a href="{BG_TOLL}" rel="nofollow">BG TOLL</a>. Сайтът е информационен; официален е списъкът на BG TOLL.</p>
  <p><a href="{up}privacy.html" lang="en">Privacy</a> · <a href="{up}support.html" lang="en">Support</a> · <a href="{up}en/" lang="en" hreflang="en">English</a> · <a href="{up}fonts/Onest-OFL.txt">Шрифт Onest (OFL)</a></p>
</div></footer>
</body>
</html>
"""


def sign(limit, size="md"):
    return f'<span class="sign sign-{size}" role="img" aria-label="Ограничение {limit} km/h">{limit}</span>'


def cta(text="Road Monitor мери средната ти скорост в зоната и казва дали си под лимита, още докато караш."):
    return f"""<aside class="cta">
  <p>{esc(text)}</p>
  <a class="button" href="{APP_URL}">Изтегли от App Store</a>
</aside>"""


def route_points(z, step=4):
    pts = z["route"]
    if len(pts) > 60:
        pts = pts[::step] + [pts[-1]]
    return [[round(a, 5), round(b, 5)] for a, b in pts]


# MARK: - Pages

def home(base, roads):
    total = sum(len(r.zones) for r in roads)
    road_cards = "\n".join(
        f'<a class="road-card" href="sredna-skorost/{r.slug}/"><strong>{esc(r.display)}</strong>'
        f'<span>{len(r.zones)} {"отсечка" if len(r.zones) == 1 else "отсечки"} · {fmt_km(r.length_km * 1000)} км</span></a>'
        for r in roads)
    schema = {
        "@context": "https://schema.org", "@type": "MobileApplication",
        "name": "Road Monitor", "operatingSystem": "iOS", "applicationCategory": "NavigationApplication",
        "inLanguage": ["bg", "en"], "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
        "url": f"{base}/", "downloadUrl": APP_URL,
        "description": "Пътна обстановка в България и контрол на средната скорост в зоните на тол камерите."}
    body = f"""<section class="band band-under hero">
  <p class="eyebrow">Приложение за iPhone</p>
  <h1>Средна скорост и пътна обстановка в България</h1>
  <p class="lead">Road Monitor мери средната ти скорост в зоните на тол камерите и казва дали си под лимита. Показва катастрофи, затворени пътища и задръствания по пътя ти.</p>
  <a class="button button-light" href="{APP_URL}">Изтегли от App Store</a>
</section>

<section class="grid3">
  <div class="tile"><h2>Средна скорост</h2><p>{total} отсечки с контрол на средна скорост. Приложението разпознава зоната, мери средната скорост от началото ѝ и показва колко си под или над лимита.</p></div>
  <div class="tile"><h2>Пътна обстановка</h2><p>Катастрофи, затворени пътища и ленти от АПИ и TomTom. Известия за твоите пътища и за това, което е пред теб.</p></div>
  <div class="tile"><h2>Без да гледаш телефона</h2><p>Заключеният екран, Dynamic Island, CarPlay и Apple Watch показват средната скорост с един поглед. Пътуванията остават на телефона ти.</p></div>
</section>

<section>
  <h2>Отсечки със средна скорост по пътища</h2>
  <div class="roads">
{road_cards}
  </div>
  <p><a href="sredna-skorost/">Всички отсечки на карта →</a> · <a href="vodach/kontrol-na-sredna-skorost/">Как работи контролът на средна скорост →</a></p>
</section>
"""
    return page(base, "", "Средна скорост и пътна обстановка в България – Road Monitor",
                f"Приложение за iPhone: контрол на средна скорост по {total} отсечки на тол камерите, карта на отсечките и пътна обстановка в България – катастрофи, затворени пътища, задръствания.",
                body, schema=schema, en_alternate=True)


def hub(base, roads):
    total = sum(len(r.zones) for r in roads)
    sections = []
    for r in roads:
        rows = "\n".join(
            f'<tr><td><a href="{r.slug}/{zone_slug(z)}/">{esc(z["name"])}</a></td>'
            f'<td class="num">{fmt_km(z["approxLengthM"])} км</td><td class="num">{sign(z["speedLimitKmh"], "sm")}</td></tr>'
            for z in r.zones)
        sections.append(f"""<section class="road-block">
  <h2><a href="{r.slug}/">{esc(r.display)}</a> <small>{len(r.zones)} отсечки</small></h2>
  <table class="zones"><thead><tr><th>Отсечка</th><th class="num">Дължина</th><th class="num">Лимит</th></tr></thead><tbody>
{rows}
  </tbody></table>
</section>""")
    map_data = {"zones": [{"n": z["name"], "l": z["speedLimitKmh"], "u": f"{r.slug}/{zone_slug(z)}/",
                           "p": route_points(z, 8)} for r in roads for z in r.zones]}
    body = f"""<section class="band band-neutral">
  <p class="eyebrow">Карта и списък</p>
  <h1>Контрол на средна скорост: всички {total} отсечки</h1>
  <p class="lead">Отсечките, в които тол камерите мерят средната скорост, по пътища и посоки. За всяка има лимит, дължина и за колко най-бързо се минава, без да надвишиш средната скорост.</p>
</section>
<div id="map" class="map" aria-label="Карта на отсечките"></div>
{"".join(sections)}
{cta()}
"""
    return page(base, "sredna-skorost/", f"Отсечки със средна скорост – карта и списък на всички {total} участъка",
                f"Карта и списък на {total} отсечки с контрол на средна скорост в България: АМ „Тракия“, „Струма“, „Хемус“, „Марица“, I-5 и др. Лимит и дължина на всеки участък.",
                body, crumbs=[("Начало", ""), ("Средна скорост", "sredna-skorost/")], map_data=map_data)


def road_page(base, road, roads):
    pairs, seen = [], set()
    for z in road.zones:
        if z["id"] in seen:
            continue
        seen.add(z["id"])
        rev = z["reverse"] if z["reverse"] and z["reverse"]["road"] == road.name else None
        if rev:
            seen.add(rev["id"])
        pairs.append((z, rev))
    rows = []
    for z, rev in pairs:
        for x in [z, rev] if rev else [z]:
            t = x["approxLengthM"] / 1000 / x["speedLimitKmh"] * 3600
            kms = f'км {esc(x["startKm"])} – {esc(x["endKm"])}' if x.get("startKm") else ""
            rows.append(f'<tr><td><a href="{zone_slug(x)}/">{esc(x["name"])}</a><small>{kms}</small></td>'
                        f'<td class="num">{fmt_km(x["approxLengthM"])} км</td>'
                        f'<td class="num">{sign(x["speedLimitKmh"], "sm")}</td>'
                        f'<td class="num">{fmt_duration(t)}</td></tr>')
    limits = sorted({z["speedLimitKmh"] for z in road.zones})
    limit_text = " и ".join(f"{l} km/h" for l in limits)
    longest = max(road.zones, key=lambda z: z["approxLengthM"])
    others = " · ".join(f'<a href="../{r.slug}/">{esc(r.display)}</a>' for r in roads if r is not road)
    faq = [
        (f"Колко отсечки за средна скорост има по {road.display}?",
         f"В каталога на Road Monitor има {len(road.zones)} отсечки по {road.display} (броят е по посоки), общо около {fmt_km(road.length_km * 1000)} км."),
        (f"Какъв е лимитът в отсечките по {road.display}?",
         f"Средната скорост се сравнява с {limit_text}. Лимитът на всяка отсечка е в таблицата по-горе."),
        (f"Коя е най-дългата отсечка по {road.display}?",
         f"{longest['name']}, около {fmt_km(longest['approxLengthM'])} км. При {longest['speedLimitKmh']} km/h се минава за не по-малко от {fmt_duration(longest['approxLengthM'] / 1000 / longest['speedLimitKmh'] * 3600)}."),
    ]
    faq_html = "\n".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
    schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    map_data = {"zones": [{"n": z["name"], "l": z["speedLimitKmh"], "u": f"{zone_slug(z)}/", "p": route_points(z)}
                          for z in road.zones]}
    body = f"""<section class="band band-neutral">
  <p class="eyebrow">{esc(road.kind.capitalize())}</p>
  <h1>Средна скорост по {esc(road.display)}: {len(road.zones)} отсечки</h1>
  <p class="lead">Всички участъци с контрол на средна скорост по {esc(road.display)}: от кой до кой километър са, колко са дълги, какъв е лимитът и за колко време най-рано можеш да ги минеш.</p>
</section>
<div id="map" class="map" aria-label="Карта на отсечките по {esc(road.display)}"></div>
<table class="zones wide"><thead><tr><th>Отсечка</th><th class="num">Дължина</th><th class="num">Лимит</th><th class="num">Най-малко време</th></tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table>
<p class="note">„Най-малко време“ е колко трае отсечката, ако караш точно с ограничението през цялото време. Ако я минеш за по-малко, средната ти скорост е над лимита.</p>
<h2>Въпроси</h2>
{faq_html}
{cta()}
<p class="more">Други пътища: {others}</p>
"""
    return page(base, f"sredna-skorost/{road.slug}/",
                f"Средна скорост {road.display} – {len(road.zones)} отсечки, лимити и карта",
                f"Отсечките с контрол на средна скорост по {road.display}: километри, дължина, лимит {limit_text} и най-малкото време за всеки участък. Карта и списък.",
                body, schema=schema, map_data=map_data,
                crumbs=[("Начало", ""), ("Средна скорост", "sredna-skorost/"), (road.display, f"sredna-skorost/{road.slug}/")])


def zone_page(base, road, z):
    L = z["approxLengthM"]
    limit = z["speedLimitKmh"]
    t_min = L / 1000 / limit * 3600
    # A few whole-minute times around the limit: what average each one means.
    minute = int(t_min // 60)
    rows = []
    for m in range(max(1, minute - 2), minute + 4):
        avg = L / 1000 / (m * 60) * 3600
        state = "over" if avg > limit else "under"
        verdict = f"{avg - limit:.0f} над лимита" if avg > limit else (
            "на лимита" if round(avg) == limit else f"{limit - avg:.0f} под лимита")
        rows.append(f'<tr class="{state}"><td class="num">{m} мин</td><td class="num">{avg:.0f} km/h</td><td>{verdict}</td></tr>')
    rev = z["reverse"]
    rev_html = (f'<p>Обратната посока: <a href="../{zone_slug(rev)}/">{esc(rev["name"])}</a>.</p>'
                if rev and rev["road"] == road.name else "")
    siblings = [x for x in road.zones if x is not z and x is not rev][:6]
    sib_html = " · ".join(f'<a href="../{zone_slug(x)}/">{esc(x["name"])}</a>' for x in siblings)
    kms = (f"от км {esc(z['startKm'])} до км {esc(z['endKm'])}" if z.get("startKm") else "")
    title = f"Средна скорост {z['from']} – {z['to']} ({road.display}): лимит {limit}, {fmt_km(L)} км"
    map_data = {"zones": [{"n": z["name"], "l": limit, "u": "", "p": route_points(z, 2)}], "ends": True}
    body = f"""<section class="band band-neutral zone-head">
  <div>
    <p class="eyebrow">{esc(road.display)} · посока {esc(z['to'])}</p>
    <h1>{esc(z['from'])} → {esc(z['to'])}</h1>
    <p class="lead">Отсечка за контрол на средна скорост, {fmt_km(L)} км {kms}.</p>
  </div>
  {sign(limit, "lg")}
</section>
<section class="figures">
  <div class="tile"><span>Лимит</span><strong>{limit} km/h</strong></div>
  <div class="tile"><span>Дължина</span><strong>{fmt_km(L)} км</strong></div>
  <div class="tile"><span>Най-малко време</span><strong>{fmt_duration(t_min)}</strong></div>
</section>
<div id="map" class="map map-sm" aria-label="Карта на отсечката"></div>
<h2>За колко време да я минеш</h2>
<p>Камерата в началото и тази в края записват кога минаваш. Средната скорост е дължината на отсечката, разделена на това време. Ако минеш {fmt_km(L)} км за по-малко от {fmt_duration(t_min)}, средната ти скорост е над {limit} km/h.</p>
<table class="times"><thead><tr><th class="num">Време</th><th class="num">Средна скорост</th><th>Спрямо лимита</th></tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table>
{rev_html}
{cta("Road Monitor разпознава тази отсечка сам, мери средната ти скорост от началото ѝ и я показва на заключения екран и в CarPlay.")}
<p class="more">Още по {esc(road.display)}: {sib_html} · <a href="../">всички {len(road.zones)} отсечки</a></p>
"""
    return page(base, zone_path(road, z), title,
                f"Отсечка {z['from']} – {z['to']} по {road.display}: лимит {limit} km/h, {fmt_km(L)} км, най-малко {fmt_duration(t_min)}. Таблица време → средна скорост и карта.",
                body, map_data=map_data,
                crumbs=[("Начало", ""), ("Средна скорост", "sredna-skorost/"),
                        (road.display, f"sredna-skorost/{road.slug}/"), (z["name"], zone_path(road, z))])


# MARK: - Guides

def guides(base, roads):
    total = sum(len(r.zones) for r in roads)
    motorways = [r for r in roads if r.is_motorway]
    first = max(roads, key=lambda r: len(r.zones))
    ex = next(z for z in first.zones if z["id"] == "vakarel-ihtiman") if any(
        z["id"] == "vakarel-ihtiman" for z in first.zones) else first.zones[0]
    ex_t = ex["approxLengthM"] / 1000 / ex["speedLimitKmh"] * 3600
    faq = [
        ("Как се изчислява средната скорост?",
         "Камера в началото на отсечката и камера в края записват кога минава автомобилът. Средната скорост е дължината на отсечката, разделена на времето между двете камери."),
        ("От кога работи контролът на средна скорост?",
         "По данни на МВР, цитирани от БТА, файловете с нарушения за средна скорост от тол камерите са от 7 септември 2025 г. насам."),
        ("Къде е официалният списък с отсечките?",
         "На сайта на BG TOLL (Националното тол управление) се публикуват сертифицираните отсечки. Road Monitor ползва този списък."),
        ("Как да проверя дали имам глоба?",
         "Задълженията към КАТ се проверяват в портала за електронни услуги на МВР (e-uslugi.mvr.bg)."),
        ("Колко е глобата за превишена средна скорост?",
         "Размерът се определя от Закона за движението по пътищата и зависи от това с колко е превишена скоростта. Не публикуваме суми, защото законът се променя: проверявайте в актуалния текст на закона."),
    ]
    faq_html = "\n".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)
    schema = [
        {"@context": "https://schema.org", "@type": "Article",
         "headline": "Контрол на средна скорост в България: как работи и как да не превишиш",
         "inLanguage": "bg", "datePublished": datetime.date.today().isoformat(),
         "author": {"@type": "Organization", "name": "Road Monitor"}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]
    road_list = ", ".join(f'<a href="../../sredna-skorost/{r.slug}/">{esc(r.display)}</a>' for r in motorways)
    body = f"""<article class="guide">
<section class="band band-neutral">
  <p class="eyebrow">Наръчник</p>
  <h1>Контрол на средна скорост в България: как работи и как да не превишиш</h1>
  <p class="lead">Две камери, едно време и едно деление. Какво точно мерят тол камерите, по кои пътища и как да знаеш средната си скорост, преди да е станала проблем.</p>
</section>

<p>Средната скорост не се интересува колко бързо си минал под камерата. Интересува се колко време ти е отнело цялото разстояние между двете камери. Затова „намалявам пред камерата“ тук не работи.</p>

<h2>Как се мери</h2>
<p>В началото и в края на всяка отсечка има камера. И двете записват кога минава колата ти. Средната скорост е дължината на отсечката, разделена на времето между двете снимки.</p>
<p>Пример: <a href="../../{zone_path(first, ex)}">{esc(ex['name'])}</a> по {esc(first.display)} е {fmt_km(ex['approxLengthM'])} км с лимит {ex['speedLimitKmh']} km/h. Ако я минеш за по-малко от {fmt_duration(ex_t)}, средната ти скорост е над лимита, колкото и бавно да си минал под самите камери.</p>

<h2>От кога и къде</h2>
<p>По данни на МВР, цитирани от <a href="{BTA_38000}" rel="nofollow">БТА</a>, нарушенията за средна скорост от тол камерите се записват от 7 септември 2025 г. Отсечките се сертифицират и публикуват от <a href="{BG_TOLL}" rel="nofollow">BG TOLL</a>, а списъкът расте.</p>
<p>В каталога на Road Monitor в момента има <a href="../../sredna-skorost/">{total} отсечки</a> по посоки. Най-много са по {esc(first.display)} ({len(first.zones)}). По магистралите: {road_list}.</p>

<h2>Защо е лесно да превишиш, без да усетиш</h2>
<p>На магистрала 10 km/h отгоре не се усещат. Кратко изпреварване със 160, после обратно на 140, и средната вече е над лимита. А отсечките са дълги: най-дългата в каталога е <a href="../../{zone_path(*max(((r, z) for r in roads for z in r.zones), key=lambda rz: rz[1]['approxLengthM']))}">{esc(max((z for r in roads for z in r.zones), key=lambda z: z['approxLengthM'])['name'])}</a>, около {fmt_km(max(z['approxLengthM'] for r in roads for z in r.zones))} км.</p>
<p>Скоростомерът показва моментната скорост. Средната за отсечката никой автомобил не я показва сам.</p>

<h2>Как да знаеш средната си скорост в момента</h2>
<p>Road Monitor разпознава началото на отсечката и от там мери средната ти скорост, точно както камерите. На заключения екран, в Dynamic Island и в CarPlay виждаш едно число и цвят: зелено, ако си под лимита, червено, ако си над него, и с колко.</p>
<p>Няма нужда да пипаш телефона в движение. В автоматичен режим измерването започва само, щом влезеш в зоната.</p>

<h2>Въпроси</h2>
{faq_html}
{cta()}
</article>
"""
    pages = {
        "vodach/kontrol-na-sredna-skorost/": page(
            base, "vodach/kontrol-na-sredna-skorost/",
            "Контрол на средна скорост: как работи и как да не превишиш – Road Monitor",
            "Как тол камерите мерят средната скорост, от кога работи контролът, къде са отсечките и как да знаеш средната си скорост, докато караш.",
            body, schema=schema,
            crumbs=[("Начало", ""), ("Наръчник", "vodach/"), ("Контрол на средна скорост", "vodach/kontrol-na-sredna-skorost/")]),
    }
    index_body = """<section class="band band-neutral">
  <p class="eyebrow">Наръчник</p>
  <h1>Наръчник за пътя</h1>
  <p class="lead">Кратки и точни ръководства за средната скорост и пътната обстановка в България.</p>
</section>
<ul class="guides">
  <li><a href="kontrol-na-sredna-skorost/"><strong>Контрол на средна скорост: как работи и как да не превишиш</strong><span>Как мерят камерите, от кога, къде са отсечките.</span></a></li>
</ul>
"""
    pages["vodach/"] = page(base, "vodach/", "Наръчник за пътя – Road Monitor",
                            "Ръководства за контрола на средна скорост и пътната обстановка в България.",
                            index_body, crumbs=[("Начало", ""), ("Наръчник", "vodach/")])
    return pages


# MARK: - Build

def write(path, text):
    out = ROOT / path / "index.html" if path.endswith("/") or path == "" else ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default=str(pathlib.Path.home() / "Development/SpeedCam/SpeedCam"))
    parser.add_argument("--base", default="https://stank0v.github.io/pace-zone-monitor-pages")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    roads = load(pathlib.Path(args.catalog).expanduser())

    # Generated trees are rebuilt from scratch, so a removed zone disappears.
    for tree in ["sredna-skorost", "vodach"]:
        shutil.rmtree(ROOT / tree, ignore_errors=True)

    pages = {"": home(base, roads), "sredna-skorost/": hub(base, roads)}
    for r in roads:
        pages[f"sredna-skorost/{r.slug}/"] = road_page(base, r, roads)
        for z in r.zones:
            pages[zone_path(r, z)] = zone_page(base, r, z)
    pages.update(guides(base, roads))
    for path, text in pages.items():
        write(path, text)

    today = datetime.date.today().isoformat()
    urls = [""] + [p for p in pages if p] + ["en/", "support.html", "privacy.html"]
    sitemap = "\n".join(f"  <url><loc>{base}/{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap}\n</urlset>\n')
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n")
    print(f"{len(pages)} pages, {sum(len(r.zones) for r in roads)} zones on {len(roads)} roads → {ROOT}")


if __name__ == "__main__":
    main()
