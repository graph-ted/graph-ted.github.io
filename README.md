# graph-ted.github.io

Source for the graph-ted organization home page (graph-ted.com).

Pre-public. This repository is private and GitHub Pages is off. Nothing here is deployed.

## Layout

| Path | What it is |
|------|------------|
| `site/` | The static site: the home page (`index.html`), CSS, a small theme-toggle script, and assets. No CDN loads. |
| `site/graph-ted-db/` | The graph-ted-db landing page at `/graph-ted-db/`. |
| `sources/graph-ted-db.ref` | The graph-ted-db commit whose docs are built into `/graph-ted-db/docs/`. |
| `site/css/tokens.css` | Generated from `tokens/tokens.json`. Do not edit by hand. |
| `site/css/site.css` | Layout and components, using only `--gt-*` variables from `tokens.css`. |
| `tokens/tokens.json` | Pinned copy of `docs/theme/tokens.json` from graph-ted-db; `tokens/SOURCE` records the commit. |
| `site/assets/logo/` | Copies of the graph-ted wordmark (from the app) and the graph-ted-db logo (from the db docs). The originals stay in those repos. |
| `site/favicon.*` | The app's circle mark favicon (home page). |
| `site/assets/favicon-db.*` | The db circle mark (copied from graph-ted-db's docs), used on the graph-ted-db landing page. The docs use the same mark. |
| `site/assets/fonts/` | Self-hosted Inter and JetBrains Mono (OFL; license texts alongside). |
| `site/assets/og.png`, `og-graph-ted-db.png` | 1200x630 social previews for the home and graph-ted-db pages, rendered by `scripts/build_og.py`. |

## Design tokens

```bash
python3 scripts/sync_tokens.py                      # regenerate site/css/tokens.css
python3 scripts/sync_tokens.py --check              # CI: fail if tokens.css is stale
python3 scripts/sync_tokens.py --from ../graph-ted-db          # re-pin from a graph-ted-db checkout
python3 scripts/sync_tokens.py --from ../graph-ted-db --check  # fail if the pin is behind that checkout
```

Page surfaces the shared tokens do not carry (page background, card, code background) are Chakra UI semantic values, listed in `SURFACES` in the script.

## Site map and where the docs come from

| URL path | Source |
|----------|--------|
| `/` | `site/index.html`, the graph-ted home page |
| `/graph-ted-db/` | `site/graph-ted-db/index.html`, the graph-ted-db landing page |
| `/graph-ted-db/docs/` | The graph-ted-db MkDocs site, built from the commit in `sources/graph-ted-db.ref` |

**Decision: one deploy, one source of truth.** This repository builds the whole site. `scripts/build_site.sh` exports the pinned graph-ted-db commit, builds its MkDocs site with `site_url` set to `https://graph-ted.com/graph-ted-db/docs/`, and writes it to `<build>/graph-ted-db/docs/` next to the pages from `site/`. To publish newer docs, bump `commit=` in `sources/graph-ted-db.ref` (a full SHA from graph-ted-db `main`) in a PR here.

> **Warning: keep GitHub Pages off in the graph-ted-db repository, permanently.** GitHub serves a project repo's Pages at `/<repo-name>/` under the org domain, so turning it on there would serve graph-ted-db at `/graph-ted-db/` and collide with the landing page and docs this repo publishes at that path. The graph-ted-db repo's `PREVIEW.md` records the same rule.

```bash
scripts/build_site.sh       # full build into build/ (needs a graph-ted-db clone with a docs venv; see the script header)
```

The build reads the pinned commit from a sibling `../graph-ted-db` clone (fetching if needed) or clones the repository into a temporary directory. While graph-ted-db is private, that needs read access to it. This repository's Pages is off and nothing deploys yet; a deploy workflow would run the same script.

The home page ("Why the database first?") and the graph-ted-db landing page link to the sharing notes at `/graph-ted-db/docs/sharing/`. `check_site.py --build` fails if that page is missing from the built docs, so the pin must stay at a graph-ted-db commit that has `docs/sharing.md`.

## Social preview

```bash
python3 scripts/build_og.py   # site/assets/og.png and og-graph-ted-db.png; needs a local Chrome/Chromium (set CHROME if not on PATH)
python3 scripts/build_og.py --variant app --out ../graph-ted/img/github-social-preview.png   # the app repo's 1280x640 preview
```

## Local preview

`scripts/preview.sh` runs `scripts/build_site.sh` with `site_url` pointed at the local server for that build only, then serves the result on `http://127.0.0.1:8004/` (`/`, `/graph-ted-db/`, and `/graph-ted-db/docs/`).

```bash
scripts/preview.sh          # build and (re)start the server in the background
scripts/preview.sh status
scripts/preview.sh stop
DOCS_REF=main scripts/preview.sh   # try unpinned docs locally (testing only)
```

Paths, host, and port are environment-overridable; see the header of the script.

## Checks

```bash
python3 scripts/check_site.py                 # HTML, local links, meta tags, no off-origin assets, copy rules
python3 scripts/check_site.py --build build   # also check /graph-ted-db/docs/ links against a full build
```
