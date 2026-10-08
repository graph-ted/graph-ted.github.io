#!/usr/bin/env bash
# Build the complete graph-ted.com site into one directory:
#
#   /                    site/ (the graph-ted home page and assets)
#   /graph-ted-db/       site/graph-ted-db/ (the graph-ted-db landing page)
#   /graph-ted-db/docs/  the graph-ted-db MkDocs site, built from the commit
#                        pinned in sources/graph-ted-db.ref
#
# This is the only way the docs reach the site. GitHub Pages stays off in the
# graph-ted-db repo: it would serve that repo at /graph-ted-db/ and collide
# with the landing page here. Nothing in this script deploys anything.
#
#   scripts/build_site.sh
#
# Environment (all optional):
#   BUILD_DIR      output directory (default <repo>/build, gitignored)
#   DB_CHECKOUT    local graph-ted-db clone to read the pinned commit from
#                  (default <repo>/../graph-ted-db; fetched from origin if the
#                  commit is missing). If it is not a clone, the repository in
#                  the pin file is cloned into a temporary directory.
#   DB_PYTHON      Python with graph-ted-db's requirements-docs.txt installed
#                  (default $DB_CHECKOUT/.venv/bin/python)
#   DOCS_SITE_URL  site_url for the docs build
#                  (default https://graph-ted.com/graph-ted-db/docs/)
#   DOCS_REF       build this ref instead of the pin (local testing only)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN_FILE="$REPO_DIR/sources/graph-ted-db.ref"
BUILD_DIR="${BUILD_DIR:-$REPO_DIR/build}"
DB_CHECKOUT="${DB_CHECKOUT:-$REPO_DIR/../graph-ted-db}"
DB_PYTHON="${DB_PYTHON:-$DB_CHECKOUT/.venv/bin/python}"
DOCS_SITE_URL="${DOCS_SITE_URL:-https://graph-ted.com/graph-ted-db/docs/}"

pin() { sed -n "s/^$1=//p" "$PIN_FILE" | head -n 1; }
DB_REPO="$(pin repository)"
DB_REF="${DOCS_REF:-$(pin commit)}"
[[ -n "$DB_REPO" && -n "$DB_REF" ]] || { echo "error: $PIN_FILE needs repository= and commit=" >&2; exit 1; }

python3 "$REPO_DIR/scripts/sync_tokens.py" --check
python3 "$REPO_DIR/scripts/check_site.py"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if git -C "$DB_CHECKOUT" rev-parse --git-dir >/dev/null 2>&1; then
  src="$DB_CHECKOUT"
  if ! git -C "$src" cat-file -e "$DB_REF^{commit}" 2>/dev/null; then
    git -C "$src" fetch --quiet origin
  fi
else
  src="$tmp/clone"
  git clone --quiet --filter=blob:none --no-checkout "$DB_REPO" "$src"
fi
commit="$(git -C "$src" rev-parse --verify "$DB_REF^{commit}")"

[[ -x "$DB_PYTHON" ]] || {
  echo "error: no docs Python at $DB_PYTHON" >&2
  echo "  create one: python3 -m venv .venv && .venv/bin/pip install -r requirements-docs.txt (in a graph-ted-db clone)" >&2
  exit 1
}

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$tmp/db"
cp -a "$REPO_DIR/site/." "$BUILD_DIR/"

git -C "$src" archive "$commit" | tar -x -C "$tmp/db"
(cd "$tmp/db" && "$DB_PYTHON" - mkdocs.yml "$DOCS_SITE_URL" <<'PY'
# Older pins hard-code site_url; set it explicitly in this throwaway export.
import re, sys
path, url = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
text, n = re.subn(r"(?m)^site_url:.*$", f"site_url: {url}", text, count=1)
if n != 1:
    text = f"site_url: {url}\n" + text
open(path, "w", encoding="utf-8").write(text)
PY
)
if ! (cd "$tmp/db" && "$DB_PYTHON" -m mkdocs build --quiet --strict \
      --site-dir "$BUILD_DIR/graph-ted-db/docs") >"$tmp/mkdocs.log" 2>&1; then
  cat "$tmp/mkdocs.log" >&2
  echo "error: docs build failed for graph-ted-db ${commit:0:7}" >&2
  exit 1
fi
echo "docs: graph-ted-db ${commit:0:7} -> $BUILD_DIR/graph-ted-db/docs (site_url $DOCS_SITE_URL)"

python3 "$REPO_DIR/scripts/check_site.py" --build "$BUILD_DIR"
echo "built: $BUILD_DIR"
