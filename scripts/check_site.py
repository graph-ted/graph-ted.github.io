#!/usr/bin/env python3
"""Sanity-check the static site in site/ (standard library only).

- every page parses; local href/src targets exist (paths under
  /graph-ted-db/docs/ are the docs build and are only checked when --build
  points at a build from scripts/build_site.sh)
- no off-origin assets: scripts, stylesheets, images, icons, fonts, and CSS
  url()s must be same-origin (outbound <a href> links are fine)
- required meta tags and canonical URL on each landing page, 1200x630 og images
- sources/graph-ted-db.ref pins a full commit; the home page and the db
  landing page link to the sharing notes (/graph-ted-db/docs/sharing/), and
  with --build that page must exist in the built docs
- copy rules: canonical domain only, no embedded-database naming

    python3 scripts/check_site.py [--build build/]
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
CANONICAL = "https://graph-ted.com/"
# Landing pages: path under site/ -> (canonical URL, og image under site/)
LANDING = {
    "index.html": (CANONICAL, "assets/og.png"),
    "graph-ted-db/index.html": (CANONICAL + "graph-ted-db/", "assets/og-graph-ted-db.png"),
}
DOCS_PREFIX = "/graph-ted-db/docs/"
SHARING = DOCS_PREFIX + "sharing/"
# Pages that must link to the sharing notes
SHARING_LINKS = ["index.html", "graph-ted-db/index.html"]
TRADEMARKS = DOCS_PREFIX + "trademarks/"
TM_LINE = "openCypher is a trademark of Neo4j, Inc."
PIN = ROOT / "sources" / "graph-ted-db.ref"
# Copy rules, written as patterns so the banned strings do not appear here.
BANNED = {
    "non-canonical domain": re.compile(r"graph(?!-)ted\.com", re.I),
    "embedded-database naming": re.compile(r"s\s*q\s*l\s*i\s*t\s*e", re.I),
    # Trademark rule: say "openCypher", never the bare language name.
    "bare query-language name (use openCypher)": re.compile(r"(?<!open)\bC[y]pher\b"),
}
REQUIRED_META = [
    ("name", "description"), ("name", "viewport"), ("property", "og:title"),
    ("property", "og:description"), ("property", "og:image"), ("property", "og:url"),
    ("name", "twitter:card"), ("name", "twitter:image"),
]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str, str]] = []  # (tag, attr, url)
        self.meta: dict[tuple[str, str], list[str]] = {}
        self.canonical = None
        self.title = False
        self.imgs_without_alt = 0
        self.has = {"header": 0, "main": 0, "footer": 0, "nav": 0, "h1": 0}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.has:
            self.has[tag] += 1
        if tag == "title":
            self.title = True
        if tag == "img" and "alt" not in a:
            self.imgs_without_alt += 1
        if tag == "meta":
            for k in ("name", "property"):
                if k in a:
                    self.meta.setdefault((k, a[k]), []).append(a.get("content", ""))
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        for attr in ("href", "src"):
            if attr in a and a[attr] is not None:
                self.links.append((tag, attr, a[attr]))


def png_size(path: Path):
    head = path.read_bytes()[:24]
    return struct.unpack(">II", head[16:24])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", type=Path, help="build dir from build_site.sh (checks /graph-ted-db/docs/ links too)")
    args = ap.parse_args()
    base = args.build or SITE
    errors: list[str] = []

    for path in sorted(SITE.rglob("*")):
        if path.suffix in {".html", ".css", ".js", ".txt", ".svg"} and "OFL" not in path.name:
            text = path.read_text(encoding="utf-8")
            for what, pat in BANNED.items():
                if pat.search(text):
                    errors.append(f"{path.relative_to(ROOT)}: {what}")

    for css in SITE.rglob("*.css"):
        for url in re.findall(r"url\(\s*['\"]?([^'\")]+)", css.read_text(encoding="utf-8")):
            if urlsplit(url).scheme or url.startswith("//"):
                errors.append(f"{css.relative_to(ROOT)}: off-origin url({url})")

    for html in sorted(SITE.rglob("*.html")):
        rel = html.relative_to(ROOT)
        p = Page()
        p.feed(html.read_text(encoding="utf-8"))
        landing = LANDING.get(html.relative_to(SITE).as_posix())
        if landing:
            canonical, og_image = landing
            for key in REQUIRED_META:
                if key not in p.meta:
                    errors.append(f"{rel}: missing meta {key[1]}")
            if p.canonical != canonical:
                errors.append(f"{rel}: canonical is {p.canonical!r}, want {canonical}")
            if p.meta.get(("property", "og:url")) != [canonical]:
                errors.append(f"{rel}: og:url should be {canonical}")
            for k in (("property", "og:image"), ("name", "twitter:image")):
                if p.meta.get(k) != [CANONICAL + og_image]:
                    errors.append(f"{rel}: {k[1]} should be {CANONICAL + og_image}")
            if len(p.meta.get(("name", "theme-color"), [])) < 2:
                errors.append(f"{rel}: want light and dark theme-color")
            for tag, n in p.has.items():
                if n < 1:
                    errors.append(f"{rel}: no <{tag}>")
            if p.has["h1"] != 1:
                errors.append(f"{rel}: want exactly one <h1>")
        if not p.title:
            errors.append(f"{rel}: no <title>")
        if p.imgs_without_alt:
            errors.append(f"{rel}: {p.imgs_without_alt} <img> without alt")
        for tag, attr, url in p.links:
            parts = urlsplit(url)
            if parts.scheme in ("http", "https") or url.startswith("//"):
                if tag != "a" and not (tag == "link" and url == p.canonical):
                    errors.append(f"{rel}: off-origin asset <{tag} {attr}={url}>")
                continue
            if parts.scheme or url.startswith("#") or not parts.path:
                continue
            if parts.path.startswith(DOCS_PREFIX) and not args.build:
                continue
            target = (base / parts.path.lstrip("/")) if parts.path.startswith("/") else (html.parent / parts.path)
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                errors.append(f"{rel}: broken link {url}")
        for frag in re.findall(r'href="#([^"]+)"', html.read_text(encoding="utf-8")):
            if f'id="{frag}"' not in html.read_text(encoding="utf-8"):
                errors.append(f"{rel}: missing anchor #{frag}")

    for _, og_image in LANDING.values():
        og = SITE / og_image
        if not og.exists():
            errors.append(f"site/{og_image} missing")
        elif png_size(og) != (1200, 630):
            errors.append(f"site/{og_image} is {png_size(og)}, want (1200, 630)")

    pin = dict(
        line.split("=", 1) for line in PIN.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.startswith("#")
    ) if PIN.exists() else {}
    if pin.get("repository") != "https://github.com/graph-ted/graph-ted-db":
        errors.append("sources/graph-ted-db.ref: repository should be https://github.com/graph-ted/graph-ted-db")
    if not re.fullmatch(r"[0-9a-f]{40}", pin.get("commit", "")):
        errors.append("sources/graph-ted-db.ref: commit should be a full 40-character SHA")

    for page in SHARING_LINKS:
        if f'href="{SHARING}"' not in (SITE / page).read_text(encoding="utf-8"):
            errors.append(f"site/{page}: no link to {SHARING}")
    for page in LANDING:
        text = (SITE / page).read_text(encoding="utf-8")
        if f'href="{TRADEMARKS}"' not in text:
            errors.append(f"site/{page}: no footer link to {TRADEMARKS}")
        if TM_LINE not in text:
            errors.append(f"site/{page}: no trademark attribution line")
    if args.build:
        for page in (SHARING, TRADEMARKS):
            target = args.build / page.lstrip("/") / "index.html"
            if not target.is_file():
                errors.append(f"{page} is missing from the build ({target})")

    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if not errors:
        print("site OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
