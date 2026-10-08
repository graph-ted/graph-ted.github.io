# graph-ted.github.io

Source for the graph-ted organization home page (graph-ted.com).

Pre-public. This repository is private and GitHub Pages is off. Nothing here is deployed.

## Layout

| Path | What it is |
|------|------------|
| `site/` | The static site: `index.html`, CSS, a small theme-toggle script, and assets. No build step, no CDN loads. |
| `site/css/tokens.css` | Generated from `tokens/tokens.json`. Do not edit by hand. |
| `site/css/site.css` | Layout and components, using only `--gt-*` variables from `tokens.css`. |
| `tokens/tokens.json` | Pinned copy of `docs/theme/tokens.json` from graph-ted-db; `tokens/SOURCE` records the commit. |
| `site/assets/logo/` | Copies of the graph-ted wordmark (from the app) and the graph-ted-db logo (from the db docs). The originals stay in those repos. |
| `site/favicon.*` | The app's circle mark favicon. |
| `site/assets/fonts/` | Self-hosted Inter and JetBrains Mono (OFL; license texts alongside). |
| `site/assets/og.png` | 1200x630 social preview, rendered by `scripts/build_og.py`. |

## Design tokens

```bash
python3 scripts/sync_tokens.py                      # regenerate site/css/tokens.css
python3 scripts/sync_tokens.py --check              # CI: fail if tokens.css is stale
python3 scripts/sync_tokens.py --from ../graph-ted-db          # re-pin from a graph-ted-db checkout
python3 scripts/sync_tokens.py --from ../graph-ted-db --check  # fail if the pin is behind that checkout
```

Page surfaces the shared tokens do not carry (page background, card, code background) are Chakra UI semantic values, listed in `SURFACES` in the script.

## Social preview

```bash
python3 scripts/build_og.py   # needs a local Chrome/Chromium (set CHROME if not on PATH)
```

## Local preview

`scripts/preview.sh` copies `site/` into a build directory, builds the graph-ted-db docs into `<build>/graph-ted-db/` from a sibling checkout (with `site_url` overridden for that build only), and serves the result on `http://127.0.0.1:8004/`.

```bash
scripts/preview.sh          # build and (re)start the server in the background
scripts/preview.sh status
scripts/preview.sh stop
```

Paths, host, and port are environment-overridable; see the header of the script.

## Checks

```bash
python3 scripts/check_site.py                 # HTML, local links, meta tags, no off-origin assets, copy rules
python3 scripts/check_site.py --build build   # also check /graph-ted-db/ links against a preview build
```
