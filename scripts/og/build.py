#!/usr/bin/env python3
"""Build the site's share cards (og:image) from one template.

    python3 scripts/og/build.py                 # render every card in cards.json
    python3 scripts/og/build.py --only home,pubs
    python3 scripts/og/build.py --out /tmp/og   # render somewhere else to look first
    python3 scripts/og/build.py --write-meta    # point each page's og:image at its card
    python3 scripts/og/build.py --check         # every og:image resolves; mapping agrees
    python3 scripts/og/build.py --sheet /tmp/og # contact sheet + WhatsApp centre-crop sheet

Each card is scripts/og/card.html rendered at 1200x630 by headless Chrome
(Montserrat Bold + Inter Tight from Google Fonts, so it needs the network),
then reduced to a 256-colour PNG with Pillow. A card whose fonts or data did
not load keeps a magenta sentinel square in its corner and the build fails
rather than writing it.

Needs: Python 3, Pillow, Google Chrome (override the path with $CHROME).

After changing a card: bump "suffix" in cards.json (platforms cache images by
URL), build, --write-meta, --check, commit, deploy, then re-scrape in the
LinkedIn Post Inspector and the Facebook Sharing Debugger.
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TEMPLATE = HERE / "card.html"
CHROME = os.environ.get(
    "CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)
W, H = 1200, 630
BONE = (245, 241, 232)
SENTINEL_XY = (1180, 20)
OG_RE = re.compile(r'(<meta property="og:image" content=")([^"]*)(" />)')


def load_config():
    return json.loads((HERE / "cards.json").read_text(encoding="utf-8"))


def card_filename(cfg, card):
    return f"{card['id']}{cfg['suffix']}.png"


def card_url(cfg, card):
    return f"{cfg['site']}/{cfg['out_dir']}/{card_filename(cfg, card)}"


# ── Render ──────────────────────────────────────────────────────────────


def screenshot(card, raw_png, timeout=90):
    """Render one card with headless Chrome. Chrome writes the PNG and then
    often lingers instead of exiting, so wait for the file and kill it."""
    data = {k: v for k, v in card.items() if k not in ("id", "pages")}
    if "inset" in data:
        data["inset"] = dict(data["inset"], src="../../" + data["inset"]["src"])
    url = TEMPLATE.as_uri() + "#" + urllib.parse.quote(json.dumps(data), safe="")
    profile = tempfile.mkdtemp(prefix="og-chrome-")
    log = open(Path(profile) / "chrome.log", "w+")
    proc = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--force-device-scale-factor=1",
            f"--window-size={W},{H}",
            "--virtual-time-budget=8000",
            f"--user-data-dir={profile}",
            f"--screenshot={raw_png}",
            url,
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        deadline = time.time() + timeout
        while time.time() < deadline:
            log.seek(0)
            if "bytes written to file" in log.read():
                return
            if proc.poll() is not None:
                break
            time.sleep(0.25)
        log.seek(0)
        raise RuntimeError(f"{card['id']}: Chrome gave no screenshot\n{log.read()[-2000:]}")
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        log.close()
        shutil.rmtree(profile, ignore_errors=True)


def optimise(raw_png, out_png):
    im = Image.open(raw_png).convert("RGB")
    if im.size != (W, H):
        raise RuntimeError(f"{out_png.name}: rendered at {im.size}, expected {(W, H)}")
    px = im.getpixel(SENTINEL_XY)
    if px != BONE:
        raise RuntimeError(
            f"{out_png.name}: sentinel pixel is {px} not bone - fonts, data or the"
            " inset did not load, or the headline would not fit"
        )
    q = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    q.save(out_png, optimize=True)
    return out_png.stat().st_size


def build(cfg, only, out_dir):
    cards = [c for c in cfg["cards"] if not only or c["id"] in only]
    missing = set(only or ()) - {c["id"] for c in cards}
    if missing:
        sys.exit(f"unknown card id(s): {', '.join(sorted(missing))}")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="og-raw-"))

    def one(card):
        raw = tmp / f"{card['id']}.png"
        screenshot(card, raw)
        out = out_dir / card_filename(cfg, card)
        size = optimise(raw, out)
        return card["id"], out, size

    failed = False
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(one, c) for c in cards]
        for f in futures:
            try:
                cid, out, size = f.result()
                flag = "" if size < 120_000 else "  <- over 120KB"
                print(f"  {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}  {size / 1024:.0f}KB{flag}")
            except Exception as e:  # noqa: BLE001 - report every card, then fail
                failed = True
                print(f"  FAILED {e}", file=sys.stderr)
    shutil.rmtree(tmp, ignore_errors=True)
    if failed:
        sys.exit(1)


# ── Pages ───────────────────────────────────────────────────────────────


def page_to_card(cfg):
    mapping = {}
    for card in cfg["cards"]:
        for page in card["pages"]:
            if page in mapping:
                sys.exit(f"{page} is listed under two cards: {mapping[page]['id']} and {card['id']}")
            mapping[page] = card
    return mapping


def write_meta(cfg):
    """Point each listed page's og:image at its card, and give it
    og:image:width/height so Facebook and LinkedIn lay the card out on the
    first share instead of after a fetch."""
    changed = 0
    for page, card in page_to_card(cfg).items():
        path = ROOT / page
        html = path.read_text(encoding="utf-8")
        hits = OG_RE.findall(html)
        if len(hits) != 1:
            sys.exit(f"{page}: expected one og:image meta, found {len(hits)}")
        new = OG_RE.sub(lambda m: m.group(1) + card_url(cfg, card) + m.group(3), html)
        if 'property="og:image:width"' not in new:
            new = OG_RE.sub(
                lambda m: m.group(0)
                + f'\n  <meta property="og:image:width" content="{W}" />'
                + f'\n  <meta property="og:image:height" content="{H}" />',
                new,
            )
        if new != html:
            path.write_text(new, encoding="utf-8")
            changed += 1
    print(f"  og:image written on {changed} page(s)")


def check(cfg):
    """Every page's og:image must resolve to a file in this repo, and pages
    listed in cards.json must point at their own card."""
    mapping = page_to_card(cfg)
    problems = []
    pages = sorted(
        p for p in ROOT.rglob("*.html")
        if ".git" not in p.parts and "scripts" not in p.parts and "docs" not in p.parts
    )
    rows = []
    for path in pages:
        rel = path.relative_to(ROOT).as_posix()
        html = path.read_text(encoding="utf-8")
        hits = OG_RE.findall(html)
        if not hits:
            continue
        if len(hits) > 1:
            problems.append(f"{rel}: {len(hits)} og:image tags")
        img = hits[0][1]
        if not img.startswith(cfg["site"] + "/"):
            problems.append(f"{rel}: og:image is not an absolute {cfg['site']} URL: {img}")
            continue
        local = ROOT / img[len(cfg["site"]) + 1:]
        if not local.is_file():
            problems.append(f"{rel}: og:image does not resolve locally: {img}")
            continue
        with Image.open(local) as im:
            if im.size != (W, H):
                problems.append(f"{rel}: {local.name} is {im.size}, not {(W, H)}")
        card = mapping.get(rel)
        if card is None:
            problems.append(f"{rel}: not listed under any card in cards.json")
        elif img != card_url(cfg, card):
            problems.append(f"{rel}: og:image is {img}, cards.json says {card_url(cfg, card)}")
        w = re.search(r'<meta property="og:image:width" content="(\d+)"', html)
        h = re.search(r'<meta property="og:image:height" content="(\d+)"', html)
        if w and h and (int(w.group(1)), int(h.group(1))) != (W, H):
            problems.append(f"{rel}: og:image:width/height say {w.group(1)}x{h.group(1)}")
        tw = re.search(r'<meta name="twitter:image" content="([^"]*)"', html)
        if tw and tw.group(1) != img:
            problems.append(f"{rel}: twitter:image {tw.group(1)} differs from og:image")
        rows.append((rel, local.name, local.stat().st_size))
    for page in mapping:
        if not (ROOT / page).is_file():
            problems.append(f"cards.json lists {page}, which does not exist")
    for rel, name, size in rows:
        print(f"  {rel:<52} {name:<48} {size / 1024:>4.0f}KB")
    print(f"  {len(rows)} pages with an og:image")
    if problems:
        print("\n".join("  PROBLEM " + p for p in problems), file=sys.stderr)
        sys.exit(1)
    print("  all og:image URLs resolve and match cards.json")


# ── Look ────────────────────────────────────────────────────────────────


def sheets(cfg, src_dir, dest):
    """Contact sheet at feed size, and a sheet of WhatsApp-style centre
    squares at thumbnail size, to look at before shipping."""
    dest.mkdir(parents=True, exist_ok=True)
    cards = [(c["id"], src_dir / card_filename(cfg, c)) for c in cfg["cards"]]
    cards = [(i, p) for i, p in cards if p.is_file()]
    cols, cw, ch, gap = 3, 600, 315, 12
    rows = (len(cards) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cw + gap) + gap, rows * (ch + gap) + gap), (120, 120, 120))
    for n, (_, p) in enumerate(cards):
        im = Image.open(p).convert("RGB").resize((cw, ch), Image.LANCZOS)
        sheet.paste(im, (gap + (n % cols) * (cw + gap), gap + (n // cols) * (ch + gap)))
    sheet.save(dest / "contact-sheet.png")

    side, thumb, cols = H, 160, 6
    rows = (len(cards) + cols - 1) // cols
    crops = Image.new("RGB", (cols * (thumb + gap) + gap, rows * (thumb + gap) + gap), (120, 120, 120))
    left = (W - side) // 2
    for n, (_, p) in enumerate(cards):
        im = Image.open(p).convert("RGB").crop((left, 0, left + side, side))
        crops.paste(im.resize((thumb, thumb), Image.LANCZOS),
                    (gap + (n % cols) * (thumb + gap), gap + (n // cols) * (thumb + gap)))
    crops.save(dest / "whatsapp-crops.png")
    print(f"  {dest / 'contact-sheet.png'}\n  {dest / 'whatsapp-crops.png'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated card ids")
    ap.add_argument("--out", help="output directory (default: out_dir in cards.json)")
    ap.add_argument("--write-meta", action="store_true", help="point og:image on each page at its card")
    ap.add_argument("--check", action="store_true", help="verify every page's og:image")
    ap.add_argument("--sheet", metavar="DIR", help="write contact + crop sheets of the built cards to DIR")
    args = ap.parse_args()
    cfg = load_config()
    out_dir = Path(args.out).resolve() if args.out else ROOT / cfg["out_dir"]

    if args.write_meta or args.check or args.sheet:
        if args.write_meta:
            write_meta(cfg)
        if args.check:
            check(cfg)
        if args.sheet:
            sheets(cfg, out_dir, Path(args.sheet).resolve())
        return
    only = set(args.only.split(",")) if args.only else None
    build(cfg, only, out_dir)


if __name__ == "__main__":
    main()
