#!/usr/bin/env python3
"""Render the 1200x630 social preview image to site/assets/og.png.

Uses the committed logo, Inter, and tokens.css, and screenshots them with a
local headless Chrome or Chromium (set CHROME to the binary if it is not on
PATH). Nothing is fetched from the network.

    python3 scripts/build_og.py
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "assets" / "og.png"
W, H = 1200, 630

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
p {{ margin: 28px 0 0; font-size: 30px; color: var(--gt-muted); }}
.foot {{ height: 14px; background: var(--gt-brand); }}
.url {{ position: absolute; right: 72px; top: 0; height: 120px; display: flex; align-items: center;
  font-size: 28px; font-weight: 600; color: var(--gt-interactive); }}
</style></head>
<body>
<div class="bar"><img src="{site}/assets/logo/graph-ted.svg" alt=""></div>
<div class="url">graph-ted.com</div>
<div class="body">
<h1>Right-sized graphs that start local, share like files, and go offline.</h1>
<p>A family of tools for working with graphs.</p>
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


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "og.html"
        page.write_text(TEMPLATE.format(site=SITE.as_uri(), w=W, h=H), encoding="utf-8")
        shot = Path(tmp) / "og.png"
        subprocess.run(
            [find_chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--allow-file-access-from-files", "--force-device-scale-factor=1",
             f"--window-size={W},{H}", "--virtual-time-budget=3000",
             f"--screenshot={shot}", page.as_uri()],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        size = png_size(shot)
        if size != (W, H):
            sys.exit(f"error: rendered {size}, expected {(W, H)}")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(shot, OUT)
    print(f"wrote {OUT.relative_to(ROOT)} ({W}x{H})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
