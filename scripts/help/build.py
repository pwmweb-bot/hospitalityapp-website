#!/usr/bin/env python3
"""Turn help/<topic>/<slug>.md into the static help centre.

    python3 scripts/help/build.py
    python3 scripts/help/build.py --check

Each article is one markdown file. Front matter:

    title, topic, summary, app_screens, audience
    optional: updated, draft, order, group

draft: true stays on disk and is not written into HTML, the search index,
help-index.json or the sitemap. The same build writes:

    /help/                         help home
    /help/<topic>/                 topic page
    /help/<topic>/<slug>/          article
    /help/search.json              website search
    /help/help-index.json          drawer index. Each article has
                                   title, topic, slug, summary, app_screens,
                                   url and html. A bare app_screens value
                                   such as "rooms" matches every rooms tab.

Sitemap entries for published help URLs sit between HELP:START and HELP:END.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELP = ROOT / "help"
SITEMAP = ROOT / "sitemap.xml"
SITE = "https://hospitalityapp.co.uk"
CSS = "/style.css?v=20261016b"

# Feature pages in the "The solution" nav. Descriptions are shortened from each page.
FEATURES = [
    ("/features/rota-management/", "Rota &amp; attendance", "Shifts, availability and recorded hours."),
    ("/features/team-communication/", "Team &amp; communication", "Notices, messages and the rota diary."),
    ("/features/compliance/", "Compliance", "Daily checks, readings and reminders."),
    ("/features/payroll/", "Payroll reports", "Hours from the clock, ready to review."),
    ("/features/till-pos/", "Till / POS", "Counter and table service, tabs and bills."),
    ("/features/mobile-ordering/", "Mobile ordering", "Take the order on a phone at the table."),
    ("/features/kitchen-display/", "Kitchen display", "Tickets to the station and the pass."),
    ("/features/reservations-floor-plans/", "Reservations &amp; floor plans", "Table bookings beside the layout."),
    ("/features/stock-control/", "Stock control", "What sold, and the profit behind it."),
    ("/features/reporting/", "Reporting", "Sales, busy periods and staffing."),
    ("/features/spaces/", "Spaces &amp; function rooms", "A room booked by session or by the hour."),
    ("/features/rooms/", "Room management", "Diary, housekeeping and the room bill."),
    ("/features/events-tickets/", "Events &amp; tickets", "Sell the night and scan at the door."),
    ("/features/loyalty/", "Loyalty", "Points on the bill, kept in the wallet."),
]


def solution_nav(current_path=""):
    """The solution stays a link. The button discloses every /features/ page."""
    solution_current = ' aria-current="page"' if current_path.rstrip("/") == "/solution" else ""
    items = []
    for href, name, description in FEATURES:
        current = ' aria-current="page"' if current_path.rstrip("/") == href.rstrip("/") else ""
        items.append(
            f'<a href="{href}"{current}><strong>{name}</strong><span>{description}</span></a>'
        )
    return (
        f'<div class="nav-drop"><a href="/solution/"{solution_current}>The solution</a>'
        f'<button type="button" class="nav-drop-toggle" aria-expanded="false" aria-controls="nav-features" aria-label="Feature pages"><span aria-hidden="true"></span></button>'
        f'<div class="nav-sub" id="nav-features">{"".join(items)}</div></div>'
    )

TOPICS = [
    {
        "slug": "till",
        "title": "Till & orders",
        "mark": "Till",
        "blurb": "Take orders, split bills, run tabs and close the day.",
        "new": False,
    },
    {
        "slug": "rooms",
        "title": "Rooms",
        "mark": "Rooms",
        "blurb": "The diary, today’s arrivals, housekeeping and the room bill.",
        "new": True,
    },
    {
        "slug": "spaces",
        "title": "Spaces",
        "mark": "Spaces",
        "blurb": "Function rooms and boardrooms your guests can book.",
        "new": True,
    },
    {
        "slug": "tickets",
        "title": "Tickets",
        "mark": "Tickets",
        "blurb": "Events, ticket types, checkout questions and the door.",
        "new": True,
    },
    {
        "slug": "staff",
        "title": "Staff & pay",
        "mark": "Staff",
        "blurb": "Rota, clock-in, tips and payroll reports.",
        "new": False,
    },
    {
        "slug": "settings",
        "title": "Settings",
        "mark": "Setup",
        "blurb": "Venue details, card payments, and who can sign in.",
        "new": False,
    },
]

POPULAR = [
    ("spaces", "setting-up-a-function-room"),
    ("tickets", "scan-tickets-at-the-door"),
    ("till", "close-the-till"),
]

REQUIRED = ("title", "topic", "summary", "app_screens", "audience")

# Filenames that must not appear in published HTML, search, the drawer index or the sitemap.
# Empty now that the room diary, today, housekeeping, capacity and maintenance have shipped.
HELD_BACK = ()


def parse_front_matter(text, path):
    if not text.startswith("---\n"):
        raise SystemExit(f"{path}: missing front matter")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise SystemExit(f"{path}: front matter is not closed")
    meta = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise SystemExit(f"{path}: bad front matter line {line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [part.strip().strip("'\"") for part in value[1:-1].split(",") if part.strip()]
        elif value.lower() in ("true", "false"):
            meta[key] = value.lower() == "true"
        elif value.isdigit():
            meta[key] = int(value)
        else:
            meta[key] = value.strip("'\"")
    for key in REQUIRED:
        if key not in meta or meta[key] in ("", []):
            raise SystemExit(f"{path}: front matter needs {key}")
    meta.setdefault("draft", False)
    meta.setdefault("order", 100)
    meta.setdefault("group", "")
    meta.setdefault("updated", "2026-10-16")
    return meta, text[end + 5 :].lstrip("\n")


def inline(text):
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*")
    parts = []
    pos = 0
    for match in pattern.finditer(text):
        parts.append(html.escape(text[pos : match.start()]))
        if match.group(1) is not None:
            alt = html.escape(match.group(1))
            src = html.escape(match.group(2), quote=True)
            parts.append(f'<img src="{src}" alt="{alt}">')
        elif match.group(3) is not None:
            label = html.escape(match.group(3))
            href = html.escape(match.group(4), quote=True)
            parts.append(f'<a href="{href}">{label}</a>')
        else:
            parts.append(f"<strong>{html.escape(match.group(5))}</strong>")
        pos = match.end()
    parts.append(html.escape(text[pos:]))
    return "".join(parts)


def heading_id(text, used):
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
    slug = base
    n = 2
    while slug in used:
        slug = f"{base}-{n}"
        n += 1
    used.add(slug)
    return slug


def render_markdown(body):
    """A small subset: headings, lists, paragraphs, bold, links, images, tips."""
    lines = body.replace("\r\n", "\n").split("\n")
    html_parts = []
    headings = []
    used = set()
    i = 0

    def flush_paragraph(buf):
        text = " ".join(part.strip() for part in buf).strip()
        if not text:
            return
        if text.startswith("![") and text.endswith(")") and text.count("![") == 1:
            match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", text)
            if match:
                alt = html.escape(match.group(1))
                src = html.escape(match.group(2), quote=True)
                html_parts.append(
                    f'<figure class="hc-shot"><img src="{src}" alt="{alt}"><figcaption>{alt}</figcaption></figure>'
                )
                return
        html_parts.append(f"<p>{inline(text)}</p>")

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            slug = heading_id(title, used)
            headings.append((slug, title))
            html_parts.append(f'<h2 id="{slug}">{inline(title)}</h2>')
            i += 1
            continue
        if line.startswith("### "):
            title = line[4:].strip()
            # Numbered steps in the mockup use "1 Name it".
            step = re.match(r"^(\d+)\s+(.*)$", title)
            if step:
                html_parts.append(
                    '<div class="hc-step"><span class="hc-no">'
                    + html.escape(step.group(1))
                    + "</span><div><h3>"
                    + inline(step.group(2))
                    + "</h3>"
                )
                i += 1
                buf = []
                while i < len(lines) and lines[i].strip() and not lines[i].startswith("#"):
                    buf.append(lines[i])
                    i += 1
                flush_paragraph(buf)
                html_parts.append("</div></div>")
                continue
            html_parts.append(f"<h3>{inline(title)}</h3>")
            i += 1
            continue
        if line.startswith("> "):
            html_parts.append(f'<p class="hc-tip">{inline(line[2:].strip())}</p>')
            i += 1
            continue
        if line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:].strip())}</li>")
                i += 1
            html_parts.append("<ul>" + "".join(items) + "</ul>")
            continue
        if re.match(r"^\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
                item = re.sub(r"^\d+\. ", "", lines[i])
                items.append(f"<li>{inline(item.strip())}</li>")
                i += 1
            html_parts.append("<ol>" + "".join(items) + "</ol>")
            continue
        buf = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "- ", "> ")) and not re.match(r"^\d+\. ", lines[i]):
            buf.append(lines[i])
            i += 1
        flush_paragraph(buf)
    return "\n".join(html_parts), headings


def plain_text(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def reading_minutes(body):
    words = len(re.findall(r"[A-Za-z0-9']+", body))
    return max(1, round(words / 200))


def load_articles():
    articles = []
    for path in sorted(HELP.glob("*/*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path)
        if meta["topic"] != path.parent.name:
            raise SystemExit(f"{path}: topic {meta['topic']!r} does not match the folder")
        if path.stem != re.sub(r"[^a-z0-9-]", "", path.stem):
            raise SystemExit(f"{path}: slug must be lowercase")
        rendered, headings = render_markdown(body)
        articles.append(
            {
                "path": path,
                "slug": path.stem,
                "meta": meta,
                "body": body,
                "html": rendered,
                "headings": headings,
                "minutes": reading_minutes(body),
            }
        )
    return articles


def topic_by_slug(slug):
    for topic in TOPICS:
        if topic["slug"] == slug:
            return topic
    raise SystemExit(f"unknown topic {slug}")


def article_url(article):
    return f"/help/{article['meta']['topic']}/{article['slug']}/"


def count_label(n):
    return "1 article" if n == 1 else f"{n} articles"


def header(current="help"):
    help_attr = ' aria-current="page"' if current == "help" else ""
    return f"""<a class="skip" href="#main">Skip to content</a>
<header><a class="brand" href="/" aria-label="Hospitality App home"><img class="brand-logo" src="/assets/logo.png" alt="Hospitality App" width="645" height="84" decoding="async"></a><nav id="site-nav" aria-label="Main navigation">{solution_nav()}<a href="/pricing/">Pricing</a><a href="/multi-site/">Multi-site</a><a href="/venues/">For venues</a><a href="/blog/">Journal</a><a href="/help/"{help_attr}>Help</a><a class="drawer-login" href="https://my.hospitalityapp.co.uk/login">Log in</a><a class="drawer-trial" href="https://my.hospitalityapp.co.uk/signup">Start free trial</a><a class="button small drawer-cta" href="/demo/">Book a 15-min demo <span>↗</span></a></nav><button class="menu-toggle" aria-expanded="false" aria-controls="site-nav" aria-label="Open menu">Menu <span>+</span></button><div class="nav-actions"><a class="login" href="https://my.hospitalityapp.co.uk/login">Log in</a><a class="trial-link" href="https://my.hospitalityapp.co.uk/signup">Start free trial</a><a class="button small" href="/demo/">Book a 15-min demo <span>↗</span></a></div></header><div class="nav-scrim" hidden></div>"""


def footer():
    return """<footer id="site-footer" class="site-footer"><div class="wrap footer-shell"><div class="footer-main"><div class="footer-brand"><a class="footer-logo" href="/" aria-label="Hospitality App home"><img src="/assets/logo.png" alt="Hospitality App" width="645" height="84" loading="lazy" decoding="async"></a><p>More hospitality. Less admin.<br>Connected tools for the people<br>who make great venues happen.</p><a class="parent-brand" href="https://psychemeta.com"><span>A PRODUCT BY</span><strong>Psychemeta<span aria-hidden="true">↗</span></strong></a><div class="footer-social" aria-label="Follow Hospitality App"><a href="https://www.linkedin.com/company/hospitalityapp" aria-label="Hospitality App on LinkedIn">LinkedIn <span aria-hidden="true">↗</span></a><a href="https://x.com/hospitalityapp" aria-label="Hospitality App on X">X <span aria-hidden="true">↗</span></a></div></div><nav class="footer-column" aria-label="Product links"><h2>Product</h2><ul><li><a href="/solution/">The solution</a></li><li><a href="/features/spaces/">Spaces &amp; function rooms</a></li><li><a href="/features/rooms/">Room management</a></li><li><a href="/features/events-tickets/">Events &amp; tickets</a></li><li><a href="/features/loyalty/">Loyalty</a></li><li><a href="/pricing/">Pricing</a></li><li><a href="/multi-site/">Multi-site</a></li><li><a href="/blog/">Journal</a></li><li><a href="/guides/">Guides</a></li><li><a href="/tools/rota-template">Free rota templates</a></li><li><a href="/compare/">Compare software</a></li><li><a href="https://my.hospitalityapp.co.uk/login">Sign in</a></li></ul></nav><nav class="footer-column" aria-label="Venue links"><h2>For your venue</h2><ul><li><a href="/venues/pubs-and-bars/">Pubs &amp; bars</a></li><li><a href="/venues/restaurants/">Restaurants</a></li><li><a href="/venues/cafes/">Cafés &amp; coffee shops</a></li><li><a href="/venues/hotels/">Hotels</a></li><li><a href="/venues/bnbs/">B&amp;Bs</a></li><li><a href="/venues/">All venues</a></li></ul></nav><nav class="footer-column" aria-label="Company links"><h2>Company</h2><ul><li><a href="/help/" aria-current="page">Help centre</a></li><li><a href="/about/">About Hospitality App</a></li><li><a href="/contact/">Contact the team</a></li><li><a href="/demo/">Book a 15-min demo</a></li><li><a href="https://psychemeta.com">Explore Psychemeta</a></li><li><a href="/privacy/">Privacy policy</a></li><li><a href="/terms/">Terms of service</a></li></ul></nav></div><div class="footer-apps"><div><h2>Your venue, wherever you are.</h2><p>iPhone &amp; Android for your team. Windows for your till.</p></div><div class="store-badges" aria-label="Get Hospitality App"><a href="https://apps.apple.com/gb/app/hospitalityappuk/id6768234673" aria-label="Download Hospitality App on the Apple App Store"><img src="/assets/app-store-badge.svg" alt="Download on the App Store" width="150" height="40" decoding="async"></a><a href="https://play.google.com/store/apps/details?id=co.uk.hospitalities.staff" aria-label="Get Hospitality App for Android on Google Play"><img src="/assets/google-play-badge.svg" alt="Get it on Google Play" width="150" height="40" decoding="async"></a><a href="/till-windows" aria-label="Get Hospitality App Till for Windows"><img src="/assets/windows-badge.svg" alt="Get the till for Windows" width="150" height="40" decoding="async"></a></div></div><div class="footer-bottom"><p>© 2026 Psychemeta Ltd. All rights reserved.</p><p>Hospitality App is a <a href="https://psychemeta.com">Psychemeta</a> product.</p><a href="#main">Back to top <span aria-hidden="true">↑</span></a></div></div></footer>
<script src="/app.js?v=20261016b"></script>"""


def page(title, description, canonical, main, json_ld):
    desc = html.escape(description, quote=True)
    return f"""<!doctype html>
<html lang="en-GB">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="{desc}"><link rel="icon" href="/favicon.ico" sizes="32x32"><link rel="icon" type="image/png" sizes="48x48" href="/favicon-48-2026.png"><link rel="icon" type="image/svg+xml" href="/favicon-2026.svg"><link rel="apple-touch-icon" href="/apple-touch-icon-2026.png"><link rel="manifest" href="/site-2026.webmanifest"><meta name="application-name" content="Hospitality App"><meta name="color-scheme" content="light only"><meta name="theme-color" content="#F9F9F5"><link rel="stylesheet" href="{CSS}"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="en-GB" href="{canonical}"><meta name="robots" content="index, follow"><meta property="og:title" content="{html.escape(title, quote=True)}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{canonical}"><meta property="og:site_name" content="Hospitality App"><meta property="og:locale" content="en_GB"><meta property="og:type" content="article"><meta property="og:image" content="{SITE}/assets/images/og/default-2026.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{html.escape(title, quote=True)}"><meta name="twitter:image" content="{SITE}/assets/images/og/default-2026.png"><meta name="twitter:description" content="{desc}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,400;0,450;0,500;0,550;0,600;0,650;0,700;1,700&amp;display=swap"><script type="application/ld+json">{json_ld}</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-TJBLJRW979"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-TJBLJRW979');</script>
</head>
<body>{header()}
{main}
{footer()}</body></html>
"""


def breadcrumbs(items):
    parts = []
    for i, (name, href) in enumerate(items):
        if i:
            parts.append('<span aria-hidden="true"> / </span>')
        if href:
            parts.append(f'<a href="{href}">{html.escape(name)}</a>')
        else:
            parts.append(f'<span aria-current="page">{html.escape(name)}</span>')
    return '<nav class="seo-breadcrumb" aria-label="Breadcrumb">' + "".join(parts) + "</nav>"


def ld_breadcrumbs(canonical, items):
    elements = []
    for i, (name, href) in enumerate(items, start=1):
        item = {"@type": "ListItem", "position": i, "name": name}
        if href:
            item["item"] = SITE + href
        else:
            item["item"] = canonical
        elements.append(item)
    graph = [
        {
            "@type": "Organization",
            "@id": SITE + "/#organization",
            "name": "Hospitality App",
            "url": SITE + "/",
            "logo": SITE + "/assets/brand/logo-2026-512.png",
            "parentOrganization": {"@type": "Organization", "name": "Psychemeta Ltd"},
        },
        {
            "@type": "BreadcrumbList",
            "@id": canonical + "#breadcrumbs",
            "itemListElement": elements,
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def clear_generated():
    for path in HELP.glob("**/index.html"):
        path.unlink()
    for name in ("search.json", "help-index.json"):
        target = HELP / name
        if target.exists():
            target.unlink()
    # Drop topic directories that no longer have a generated index, but never the markdown.
    for directory in sorted(HELP.iterdir()):
        if not directory.is_dir():
            continue
        for child in list(directory.iterdir()):
            if child.is_dir() and not any(child.iterdir()):
                child.rmdir()


def home_page(published):
    by_topic = {}
    for article in published:
        by_topic.setdefault(article["meta"]["topic"], []).append(article)
    cards = []
    for topic in TOPICS:
        items = by_topic.get(topic["slug"], [])
        links = "".join(
            f'<li>{html.escape(article["meta"]["title"])}</li>' for article in items[:3]
        )
        badge = '<span class="hc-new">NEW</span>' if topic["new"] else ""
        cards.append(
            f'<a class="hc-cat" href="/help/{topic["slug"]}/"><span class="hc-mark">{html.escape(topic["mark"])}</span>'
            f'<h3>{html.escape(topic["title"])}{badge}</h3><p>{html.escape(topic["blurb"])}</p>'
            f"<ul>{links}</ul><span class=\"hc-count\">{count_label(len(items))} →</span></a>"
        )
    popular = []
    lookup = {(a["meta"]["topic"], a["slug"]): a for a in published}
    for key in POPULAR:
        article = lookup[key]
        popular.append(f'<a href="{article_url(article)}">{html.escape(article["meta"]["title"])}</a>')
    started = lookup[("settings", "getting-started")]
    canonical = SITE + "/help/"
    main = f"""<main id="main">
<section class="hc-hero"><div class="wrap">
<p class="eyebrow">Help centre</p>
<h1>How can we <em>help?</em></h1>
<p class="intro">Short, plain guides for every part of Hospitality App. The same articles are in the app, behind the ? button.</p>
<form class="hc-search" role="search" action="/help/" method="get">
<label class="skip" for="help-q">Search help</label>
<input id="help-q" name="q" type="search" placeholder="Search help, e.g. function room deposit" autocomplete="off">
<kbd aria-hidden="true">/</kbd>
</form>
<p class="hc-pop">Popular: {" ".join(popular)}</p>
<div id="help-results" class="hc-results" hidden></div>
</div></section>
<section class="section wrap"><div class="section-head"><div><p class="eyebrow">Browse by topic</p><h2>Find your way <em>around.</em></h2></div><p>Six topics, one for each part of the app. New guides are marked NEW.</p></div>
<div class="hc-cats">{"".join(cards)}</div></section>
<section class="section wrap" style="padding-top:0"><div class="hc-cta"><div><p class="eyebrow">Getting started</p><h2>New to Hospitality App?</h2><p>Set up your venue, your till and your team. Start with the checklist.</p><a class="text-link" href="{article_url(started)}">Start here <span>↗</span></a></div><div><p class="eyebrow">Still stuck</p><h2>Talk to a person.</h2><p>Send us a message from the app or this site. Tell us the screen you were on and what you expected to happen.</p><a class="text-link" href="/contact/">Contact the team <span>↗</span></a></div></div></section>
<section class="closing"><div class="wrap"><p class="eyebrow">Fifteen minutes, on your venue</p><h2>Rather see it <em>done?</em></h2><a class="button" href="/demo/">Book a 15-min demo <span>↗</span></a><p>We will walk through it on your own venue.</p></div></section>
</main>
<script src="/assets/help-search.js?v=20261016a"></script>"""
    return page(
        "Help centre | Hospitality App",
        "Short guides for the till, rooms, function rooms, tickets, staff and settings. The same articles open from the ? button in the app.",
        canonical,
        main,
        ld_breadcrumbs(canonical, [("Home", "/"), ("Help centre", None)]),
    )


def topic_page(topic, articles):
    side = []
    for item in TOPICS:
        current = ' aria-current="page"' if item["slug"] == topic["slug"] else ""
        side.append(f'<a href="/help/{item["slug"]}/"{current}>{html.escape(item["title"])}</a>')
    groups = []
    grouped = {}
    for article in articles:
        grouped.setdefault(article["meta"]["group"] or "Guides", []).append(article)
    # Preserve first-seen group order.
    for name, items in grouped.items():
        rows = []
        for article in items:
            rows.append(
                f'<a href="{article_url(article)}"><span><h3>{html.escape(article["meta"]["title"])}</h3>'
                f'<p>{html.escape(article["meta"]["summary"])}</p></span><span class="hc-go" aria-hidden="true">↗</span></a>'
            )
        groups.append(f'<section class="hc-group"><h2>{html.escape(name.upper())}</h2><div class="hc-list">{"".join(rows)}</div></section>')
    badge = ' <span class="hc-new">NEW</span>' if topic["new"] else ""
    canonical = f"{SITE}/help/{topic['slug']}/"
    main = f"""<main id="main"><div class="wrap hc-layout">
<aside class="hc-side"><h2>Topics</h2>{"".join(side)}</aside>
<div>{breadcrumbs([("Help", "/help/"), (topic["title"], None)])}
<p class="eyebrow">{html.escape(topic["title"])}</p>
<h1>{html.escape(topic["title"])}{badge}</h1>
<p class="intro">{html.escape(topic["blurb"])}</p>
<p class="hc-count">{count_label(len(articles))}</p>
{"".join(groups)}
</div></div></main>"""
    return page(
        f"{topic['title']} help | Hospitality App",
        topic["blurb"],
        canonical,
        main,
        ld_breadcrumbs(canonical, [("Home", "/"), ("Help centre", "/help/"), (topic["title"], None)]),
    )


def article_page(article, siblings):
    topic = topic_by_slug(article["meta"]["topic"])
    side = []
    for item in siblings:
        current = ' aria-current="page"' if item["slug"] == article["slug"] else ""
        side.append(f'<a href="{article_url(item)}"{current}>{html.escape(item["meta"]["title"])}</a>')
    toc = "".join(f'<a href="#{slug}">{html.escape(title)}</a>' for slug, title in article["headings"])
    audience = ", ".join(article["meta"]["audience"])
    canonical = SITE + article_url(article)
    main = f"""<main id="main"><div class="wrap hc-article">
<aside class="hc-side"><h2>{html.escape(topic["title"])}</h2>{"".join(side)}</aside>
<article>{breadcrumbs([("Help", "/help/"), (topic["title"], f"/help/{topic['slug']}/"), (article["meta"]["title"], None)])}
<p class="eyebrow">{html.escape(topic["title"])}</p>
<h1>{html.escape(article["meta"]["title"])}</h1>
<p class="hc-meta"><span>{article["minutes"]} min read</span><span>Updated {html.escape(article["meta"]["updated"])}</span><span>For {html.escape(audience)}</span></p>
<p class="intro">{html.escape(article["meta"]["summary"])}</p>
<div class="hc-body">{article["html"]}</div>
<div class="hc-feedback"><span>Did this help?</span><button type="button" data-help="yes">Yes</button><button type="button" data-help="no">No</button><a href="/contact/">Contact the team</a><span data-help-note hidden>Thanks. If you still need a hand, contact the team.</span></div>
<p class="hc-inapp"><i>?</i> This article also opens from the {html.escape(topic["title"])} screens in the app.</p>
</article>
<nav class="hc-toc" aria-label="On this page"><h2>On this page</h2>{toc}</nav>
</div></main>
<script>document.querySelectorAll("[data-help]").forEach(function(button){{button.addEventListener("click",function(){{var note=document.querySelector("[data-help-note]");note.hidden=false;}});}});</script>"""
    return page(
        f"{article['meta']['title']} | Hospitality App help",
        article["meta"]["summary"],
        canonical,
        main,
        ld_breadcrumbs(
            canonical,
            [
                ("Home", "/"),
                ("Help centre", "/help/"),
                (topic["title"], f"/help/{topic['slug']}/"),
                (article["meta"]["title"], None),
            ],
        ),
    )


def absolute_body(fragment):
    def repl(match):
        attr, url = match.group(1), match.group(2)
        if url.startswith("/"):
            url = SITE + url
        return f'{attr}="{url}"'

    return re.sub(r'(src|href)="(/[^"]*)"', repl, fragment)


def write_indexes(published):
    search = []
    drawer = []
    for article in published:
        url = article_url(article)
        search.append(
            {
                "title": article["meta"]["title"],
                "summary": article["meta"]["summary"],
                "topic": article["meta"]["topic"],
                "topicTitle": topic_by_slug(article["meta"]["topic"])["title"],
                "url": url,
                "text": plain_text(article["html"]),
            }
        )
        drawer.append(
            {
                "title": article["meta"]["title"],
                "topic": article["meta"]["topic"],
                "slug": article["slug"],
                "summary": article["meta"]["summary"],
                "app_screens": article["meta"]["app_screens"],
                "url": SITE + url,
                "html": absolute_body(article["html"]),
            }
        )
    write(HELP / "search.json", json.dumps({"articles": search}, ensure_ascii=False, indent=2) + "\n")
    write(
        HELP / "help-index.json",
        json.dumps({"articles": drawer}, ensure_ascii=False, indent=2) + "\n",
    )


def write_sitemap(published):
    urls = [f"{SITE}/help/"] + [f"{SITE}/help/{topic['slug']}/" for topic in TOPICS]
    urls += [SITE + article_url(article) for article in published]
    block = ["  <!-- HELP:START -->"]
    for url in urls:
        block.append("  <url>")
        block.append(f"    <loc>{url}</loc>")
        block.append("    <lastmod>2026-10-16</lastmod>")
        block.append("    <changefreq>monthly</changefreq>")
        block.append("    <priority>0.6</priority>")
        block.append("  </url>")
    block.append("  <!-- HELP:END -->")
    text = SITEMAP.read_text(encoding="utf-8")
    replacement = "\n".join(block)
    if "<!-- HELP:START -->" in text:
        text = re.sub(r"  <!-- HELP:START -->.*?  <!-- HELP:END -->", replacement, text, flags=re.S)
    else:
        text = text.replace("</urlset>", replacement + "\n</urlset>")
    SITEMAP.write_text(text, encoding="utf-8")


def build():
    articles = load_articles()
    known = {topic["slug"] for topic in TOPICS}
    for article in articles:
        if article["meta"]["topic"] not in known:
            raise SystemExit(f"unknown topic {article['meta']['topic']}")
    published = [article for article in articles if not article["meta"]["draft"]]
    drafts = [article for article in articles if article["meta"]["draft"]]
    published.sort(key=lambda article: (article["meta"]["order"], article["meta"]["title"]))
    clear_generated()
    by_topic = {}
    for article in published:
        by_topic.setdefault(article["meta"]["topic"], []).append(article)
    for topic in TOPICS:
        if topic["slug"] not in by_topic:
            raise SystemExit(f"topic {topic['slug']} has no published article")
    write(HELP / "index.html", home_page(published))
    for topic in TOPICS:
        items = by_topic[topic["slug"]]
        write(HELP / topic["slug"] / "index.html", topic_page(topic, items))
        for article in items:
            write(HELP / topic["slug"] / article["slug"] / "index.html", article_page(article, items))
    write_indexes(published)
    write_sitemap(published)
    return published, drafts


def check(published, drafts):
    errors = []
    published_titles = {article["meta"]["title"] for article in published}
    draft_titles = {article["meta"]["title"] for article in drafts}
    if published_titles & draft_titles:
        errors.append("a draft reuses a published title")
    blob_paths = [HELP / "index.html", HELP / "search.json", HELP / "help-index.json", SITEMAP]
    blob_paths += list(HELP.glob("**/index.html"))
    blob = "\n".join(path.read_text(encoding="utf-8") for path in blob_paths)
    for title in draft_titles:
        if title in blob:
            errors.append(f"draft title published: {title}")
    for name in HELD_BACK:
        if name in blob:
            errors.append(f"unpublished screenshot linked: {name}")
    home = (HELP / "index.html").read_text(encoding="utf-8")
    by_topic = {}
    for article in published:
        by_topic.setdefault(article["meta"]["topic"], 0)
        by_topic[article["meta"]["topic"]] += 1
    for topic in TOPICS:
        label = count_label(by_topic[topic["slug"]])
        if label not in home:
            errors.append(f"home is missing the real count {label} for {topic['slug']}")
    # The proposal's placeholder counts must not be copied onto the home.
    for fake in ("18 articles", "16 articles", "11 articles", "12 articles", "21 articles", "14 articles"):
        if fake in home and fake not in {count_label(n) for n in by_topic.values()}:
            errors.append(f"placeholder count still on the home: {fake}")
    index = json.loads((HELP / "help-index.json").read_text(encoding="utf-8"))
    if len(index["articles"]) != len(published):
        errors.append("help-index.json count does not match published articles")
    for entry in index["articles"]:
        for key in ("title", "topic", "slug", "summary", "app_screens", "url", "html"):
            if not entry.get(key):
                errors.append(f"help-index entry missing {key}: {entry.get('title')}")
        if "screens" in entry or "body" in entry:
            errors.append(f"help-index still uses the old field names: {entry.get('title')}")
        if not str(entry.get("url", "")).startswith(SITE + "/help/"):
            errors.append(f"help-index url is not absolute: {entry.get('title')}")
        screens = entry.get("app_screens")
        if not isinstance(screens, list) or not all(isinstance(s, str) and s for s in screens):
            errors.append(f"help-index app_screens is not a list of keys: {entry.get('title')}")
        if entry["url"].rstrip("/").split("/")[-1] + ".md" not in " ".join(
            article["slug"] + ".md" for article in published
        ):
            pass
        if any(article["meta"]["draft"] and article["meta"]["title"] == entry["title"] for article in drafts):
            errors.append("draft leaked into help-index.json")
    search = json.loads((HELP / "search.json").read_text(encoding="utf-8"))
    if len(search["articles"]) != len(published):
        errors.append("search.json count does not match published articles")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    for article in published:
        if SITE + article_url(article) not in sitemap:
            errors.append(f"sitemap missing {article_url(article)}")
    for article in drafts:
        if article_url(article) in sitemap:
            errors.append(f"sitemap includes draft {article_url(article)}")
    if errors:
        raise SystemExit("help build check failed:\n- " + "\n- ".join(errors))
    print(f"published {len(published)} articles, held back {len(drafts)} drafts")


def main():
    published, drafts = build()
    if "--check" in sys.argv or True:
        check(published, drafts)


if __name__ == "__main__":
    main()
