#!/usr/bin/env python3
"""Generate site/css/tokens.css from the pinned design tokens.

The tokens are shared with the graph-ted-db docs theme. tokens/tokens.json is
a pinned copy of docs/theme/tokens.json from graph-ted/graph-ted-db, and
tokens/SOURCE records the commit it came from.

    python3 scripts/sync_tokens.py                  # regenerate tokens.css
    python3 scripts/sync_tokens.py --check          # fail if tokens.css is stale
    python3 scripts/sync_tokens.py --from ../graph-ted-db          # re-pin, then regenerate
    python3 scripts/sync_tokens.py --from ../graph-ted-db --check  # also fail if the pin is stale

Standard library only. Do not edit tokens.css by hand.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "tokens" / "tokens.json"
SOURCE = ROOT / "tokens" / "SOURCE"
CSS = ROOT / "site" / "css" / "tokens.css"
DB_TOKENS = Path("docs") / "theme" / "tokens.json"

# Page surfaces the shared tokens do not carry (the docs page body is
# Material's). These are the Chakra UI semantic tokens the app uses for the
# page and panels, so the home page reads like the app around its navbar.
SURFACES = {
    "light": {
        "bg": "#ffffff",        # Chakra bg (white)
        "fg": None,             # = color.light.header_text (Chakra fg)
        "card": "#ffffff",      # Chakra bg.panel
        "code-bg": None,        # = color.light.header (bg.muted)
    },
    "dark": {
        "bg": "#09090b",        # Chakra bg (black)
        "fg": None,             # = color.dark.header_text (Chakra fg)
        "card": None,           # = color.dark.header (bg.muted)
        "code-bg": "#09090b",   # Chakra bg, so code stands off the card
    },
}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or "x"


def scheme_vars(tokens: dict, scheme: str) -> list[tuple[str, str]]:
    c = tokens["color"][scheme]
    surf = SURFACES[scheme]
    out = [
        ("bg", surf["bg"]),
        ("fg", surf["fg"] or c["header_text"]),
        ("muted", c["header_muted"]),
        ("border", c["header_border"]),
        ("card", surf["card"] or c["header"]),
        ("code-bg", surf["code-bg"] or c["header"]),
        ("header-bg", c["header"]),
        ("header-fg", c["header_text"]),
        ("header-border", c["header_border"]),
        ("link", c["link"]),
        ("accent", c["accent"]),
        ("focus", tokens["focus"][scheme]),
        ("button-bg", c.get("button_fill", tokens["color"]["interactive"])),
        ("button-fg", c.get("button_text", tokens["color"]["on_interactive"])),
    ]
    for name, val in tokens["shadow"].items():
        out.append((f"shadow-{slug(name)}", val[scheme]))
    return out


def render(tokens: dict) -> str:
    col = tokens["color"]
    root = [
        ("brand", col["brand"]),
        ("interactive", col["interactive"]),
        ("on-interactive", col["on_interactive"]),
        ("font-text", tokens["font"]["text"]),
        ("font-code", f'"{tokens["font"]["code"]}", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'),
        ("navbar-height", tokens["layout"]["navbar_height"]),
        ("logo-height", tokens["layout"]["logo_height"]),
        ("button-height", tokens["button"]["height"]),
        ("button-px", tokens["button"]["padding_x"]),
        ("button-font-size", tokens["button"]["font_size"]),
        ("button-line-height", tokens["button"]["line_height"]),
    ]
    root += [(f"radius-{slug(k)}", v) for k, v in tokens["radius"].items()]
    root += [(f"space-{slug(k)}", v) for k, v in tokens["spacing"].items()]

    def block(selector: str, pairs, scheme: str = "", indent: str = "") -> str:
        lines = [f"{selector} {{"]
        if scheme:
            lines.append(f"  color-scheme: {scheme};")
        lines += [f"  --gt-{k}: {v};" for k, v in pairs]
        lines.append("}")
        return "".join(f"{indent}{ln}\n" for ln in lines)

    light = scheme_vars(tokens, "light")
    dark = scheme_vars(tokens, "dark")
    parts = [
        "/* Generated from tokens/tokens.json by scripts/sync_tokens.py.\n"
        "   Do not edit by hand. Regenerate with: python3 scripts/sync_tokens.py\n"
        "   Light scheme by default; dark follows prefers-color-scheme unless the\n"
        "   page toggle sets data-theme on <html>. */\n",
        block(":root", root),
        block(":root", light, "light"),
        "@media (prefers-color-scheme: dark) {\n"
        + block(':root:not([data-theme="light"])', dark, "dark", "  ")
        + "}\n",
        block(':root[data-theme="dark"]', dark, "dark"),
        block(':root[data-theme="light"]', light, "light"),
    ]
    return "\n".join(parts)


def git_short_head(checkout: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", type=Path, help="graph-ted-db checkout to re-pin tokens from")
    ap.add_argument("--check", action="store_true", help="exit 1 if outputs are out of date; write nothing")
    args = ap.parse_args()

    stale = []
    if args.src:
        upstream = args.src / DB_TOKENS
        if not upstream.is_file():
            print(f"error: {DB_TOKENS} not found in the given checkout", file=sys.stderr)
            return 2
        new = upstream.read_text(encoding="utf-8")
        if args.check:
            if new != TOKENS.read_text(encoding="utf-8"):
                stale.append("tokens/tokens.json (differs from the checkout)")
        else:
            TOKENS.write_text(new, encoding="utf-8")
            lines = SOURCE.read_text(encoding="utf-8").splitlines() if SOURCE.exists() else []
            lines = [ln for ln in lines if not ln.startswith("commit:")]
            SOURCE.write_text("\n".join(lines + [f"commit: {git_short_head(args.src)}"]) + "\n", encoding="utf-8")

    css = render(json.loads(TOKENS.read_text(encoding="utf-8")))
    if args.check:
        if not CSS.exists() or CSS.read_text(encoding="utf-8") != css:
            stale.append("site/css/tokens.css (run scripts/sync_tokens.py)")
        for s in stale:
            print(f"stale: {s}", file=sys.stderr)
        if not stale:
            print("tokens OK")
        return 1 if stale else 0
    CSS.parent.mkdir(parents=True, exist_ok=True)
    CSS.write_text(css, encoding="utf-8")
    print(f"wrote {CSS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
