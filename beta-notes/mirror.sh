#!/usr/bin/env bash
#
# mirror.sh — Model B addon-source mirror: ha-addons-beta → ha-addons (prod)
#
# Beta is the source of truth. You author and test the LibreCoach add-on in
# ha-addons-beta, then run this to push the *shared addon source* up to the prod
# ha-addons repo (currently the release-integration branch) ahead of a
# release.
#
# Synced surface: librecoach/ ONLY, minus build/branding files. Everything else
# (repo root, .github/, can-mqtt-bridge/, beta-notes/) is intentionally
# repo-specific and is never touched — see beta_sync_plan.md for the rationale.
#
# SAFETY: dry-run by default. Nothing is written unless you pass --apply.
#
set -euo pipefail

# --- locate both repos (they are siblings under .../librecoach/) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BETA="$(cd "$SCRIPT_DIR/.." && pwd)"          # ha-addons-beta (this repo)
PROD="$(cd "$BETA/.." && pwd)/ha-addons"      # ha-addons (prod), sibling dir

SRC="$BETA/librecoach/"                        # trailing slash: copy CONTENTS
DST="$PROD/librecoach/"

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

# --- sanity checks ---
[[ -d "$SRC" ]] || { echo "ERROR: beta source missing: $SRC" >&2; exit 1; }
[[ -d "$DST" ]] || { echo "ERROR: prod dest missing: $DST" >&2; exit 1; }
[[ -d "$PROD/.git" ]] || { echo "ERROR: $PROD is not a git repo" >&2; exit 1; }

# Files that must stay prod-specific (Option A: config.yaml carries prod's
# version + image line) plus transient build artifacts.
RSYNC_OPTS=(
  -a --checksum --delete --itemize-changes --human-readable
  --exclude='config.yaml'
  --exclude='__pycache__/'
  --exclude='.pytest_cache/'
  --exclude='.benchmarks/'
  --exclude='*.pyc'
  --exclude='.coverage'
  --exclude='htmlcov/'
)

echo "Model B mirror — beta ➜ prod (addon source only)"
echo "  source: $SRC"
echo "  dest:   $DST  [$(git -C "$PROD" rev-parse --abbrev-ref HEAD)]"
echo

if [[ $APPLY -eq 1 ]]; then
  echo ">>> APPLYING — writing to prod <<<"
  rsync "${RSYNC_OPTS[@]}" "$SRC" "$DST"
else
  echo "DRY RUN — no changes written. Re-run with --apply to mirror."
  rsync --dry-run "${RSYNC_OPTS[@]}" "$SRC" "$DST"
fi

# --- config.yaml drift check (Option A: must differ ONLY by version + image) ---
echo
echo "config.yaml check (must differ only on 'version:' and 'image:') ..."
python3 - "$SRC/config.yaml" "$DST/config.yaml" <<'PYEOF'
import sys
beta = open(sys.argv[1]).read().splitlines()
prod = open(sys.argv[2]).read().splitlines()
import difflib
offenders = []
for line in difflib.unified_diff(prod, beta, lineterm=""):
    if line[:1] in "+-" and line[:2] not in ("++", "--"):
        key = line[1:].split(":", 1)[0].strip()
        if key not in ("version", "image"):
            offenders.append(line)
if offenders:
    print("  ⚠️  config.yaml differs beyond version/image — port these by hand to prod:")
    for o in offenders:
        print("     ", o)
else:
    print("  ✓ only version/image differ (or identical) — nothing to port")
PYEOF

echo
if [[ $APPLY -eq 1 ]]; then
  cat <<EOF
Next, in $PROD:
  1. Apply any config.yaml option/schema changes flagged above (keep prod version+image).
  2. Run the add-on tests:  (cd librecoach/librecoach_ble/tests && python3 -m pytest -q)
  3. Review:  git -C "$PROD" status  &&  rtk proxy git -C "$PROD" diff
  4. Commit on release-integration (do NOT merge to main without approval).
EOF
fi
