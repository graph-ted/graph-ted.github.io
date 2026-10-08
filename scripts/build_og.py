#!/usr/bin/env python3
"""Render social preview images in the graph-ted og style.

Uses the committed logos, Inter, and tokens.css, and screenshots them with a
local headless Chrome or Chromium (set CHROME to the binary if it is not on
PATH). Nothing is fetched from the network.

    python3 scripts/build_og.py                  # site/assets/og.png and og-graph-ted-db.png
    python3 scripts/build_og.py --variant app --out ../graph-ted/img/github-social-preview.png

Variants: root (graph-ted home), db (graph-ted-db landing), app (the
graph-ted app repo's GitHub social preview, 1280x640).
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

VARIANTS = {
    "root": dict(
        out=SITE / "assets" / "og.png", size=(1200, 630), logo="graph-ted.svg", url="graph-ted.com",
        headline="A free toolkit for knowledge graphs.",
        sub="Create, store, and explore connected knowledge.",
    ),
    "db": dict(
        out=SITE / "assets" / "og-graph-ted-db.png", size=(1200, 630), logo="graph-ted-db.svg",
        url="graph-ted.com/graph-ted-db",
        headline="A graph database in a folder.",
        sub="No server, shares like files.",
    ),
    "app": dict(
        out=None, size=(1280, 640), logo="graph-ted.svg", url="graph-ted.com",
        headline="Build and explore knowledge graphs.",
        sub="A workspace with AI that turns notes and conversations into connected knowledge.",
    ),
}

TEMPLATE = """<!doctype html>
<html lang="en" data-theme="light"><head><meta charset="utf-8">
<link rel="stylesheet" href="{site}/css/tokens.css">
<style>
@font-face {{ font-family: "Inter"; font-weight: 100 900;
  src: url("{site}/assets/fonts/InterVariable.woff2") format("woff2"); }}
html, body {{ margin: 0; width: {w}px; height: {h}px; overflow: hidden; }}
body {{ background: var(--gt-bg); color: var(--gt-fg); font-family: var(--gt-font-text);
  display: flex; flex-direction: column; }}
.bar {{ height: 120px; background: var(--gt-header-bg); border-bottom: 1px solid var(--gt-header-border);
  display: flex; align-items: center; padding: 0 72px; }}
.bar img {{ height: 96px; }}
.body {{ flex: 1; display: flex; flex-direction: column; justify-content: center; padding: 0 72px; }}
h1 {{ margin: 0; font-size: 64px; line-height: 1.08; letter-spacing: -0.025em; font-weight: 700; max-width: 960px; }}
p {{ margin: 28px 0 0; font-size: 30px; color: var(--gt-muted); max-width: 1000px; }}
.foot {{ height: 14px; background: var(--gt-brand); }}
.url {{ position: absolute; right: 72px; top: 0; height: 120px; display: flex; align-items: center;
  font-size: 28px; font-weight: 600; color: var(--gt-interactive); }}
</style></head>
<body>
<div class="bar"><img src="{site}/assets/logo/{logo}" alt=""></div>
<div class="url">{url}</div>
<div class="body">
<h1>{headline}</h1>
<p>{sub}</p>
</div>
<div class="foot"></div>
</body></html>
"""


def find_chrome() -> str:
    env = os.environ.get("CHROME")
    if env:
        return env
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("error: no Chrome/Chromium found; set CHROME")


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def render(variant: str, out: Path) -> None:
    v = VARIANTS[variant]
    w, h = v["size"]
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "og.html"
        page.write_text(TEMPLATE.format(site=SITE.as_uri(), w=w, h=h, logo=v["logo"], url=v["url"],
                                        headline=v["headline"], sub=v["sub"]), encoding="utf-8")
        shot = Path(tmp) / "og.png"
        subprocess.run(
            [find_chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--allow-file-access-from-files", "--force-device-scale-factor=1",
             f"--window-size={w},{h}", "--virtual-time-budget=3000",
             f"--screenshot={shot}", page.as_uri()],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        size = png_size(shot)
        if size != (w, h):
            sys.exit(f"error: rendered {size}, expected {(w, h)}")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(shot, out)
    print(f"wrote {out} ({w}x{h}, {variant})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=sorted(VARIANTS), action="append",
                    help="variant to render (repeatable; default: root and db)")
    ap.add_argument("--out", type=Path, help="output path (required for app; single variant only)")
    args = ap.parse_args()
    variants = args.variant or ["root", "db"]
    if args.out and len(variants) != 1:
        ap.error("--out takes exactly one --variant")
    for name in variants:
        out = args.out or VARIANTS[name]["out"]
        if out is None:
            ap.error(f"--variant {name} needs --out")
        render(name, out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
