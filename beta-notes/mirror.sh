#!/usr/bin/env bash
#
# mirror.sh — Model B addon-source mirror: ha-addons-beta → ha-addons (prod)
#
# Beta is the source of truth. You author and test the LibreCoach add-on in
# ha-addons-beta, then run this to push the *shared addon source* up to prod
# ha-addons main ahead of a release. It reads branch names live for reporting;
# apply mode requires prod to be checked out on main.
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

# Branch names are read live (never hardcoded) so this script is reusable across cycles.
BETA_BRANCH="$(git -C "$BETA" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
PROD_BRANCH="$(git -C "$PROD" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

# --- sanity checks ---
[[ -d "$SRC" ]] || { echo "ERROR: beta source missing: $SRC" >&2; exit 1; }
[[ -d "$DST" ]] || { echo "ERROR: prod dest missing: $DST" >&2; exit 1; }
[[ -d "$PROD/.git" ]] || { echo "ERROR: $PROD is not a git repo" >&2; exit 1; }
if [[ $APPLY -eq 1 && "$PROD_BRANCH" != "main" ]]; then
  echo "ERROR: prod must be checked out on main before applying the mirror (currently: $PROD_BRANCH)" >&2
  exit 1
fi

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
echo "  source: $SRC  [$BETA_BRANCH]"
echo "  dest:   $DST  [$PROD_BRANCH]"
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

# --- translations parity check (es.yaml must always mirror en.yaml's keys) ---
echo
echo "translations check (en.yaml vs es.yaml keys) ..."
python3 - "$SRC/translations/en.yaml" "$SRC/translations/es.yaml" <<'PYEOF'
import sys, re
def keys(p):
    return [m.group(1) for l in open(p) if (m := re.match(r"  (\w+):", l))]
en = keys(sys.argv[1]); es = keys(sys.argv[2])
missing = [k for k in en if k not in es]
extra   = [k for k in es if k not in en]
if missing or extra:
    print("  ⚠️  en.yaml / es.yaml key mismatch — keep translations in sync:")
    if missing: print("     missing from es.yaml:", ", ".join(missing))
    if extra:   print("     extra in es.yaml:    ", ", ".join(extra))
else:
    print("  ✓ en.yaml and es.yaml have matching keys")
PYEOF

echo
if [[ $APPLY -eq 1 ]]; then
  cat <<EOF
Next, in $PROD:
  1. Apply any config.yaml option/schema changes flagged above (keep prod version+image).
  2. Run the add-on tests:  (cd librecoach/librecoach_ble/tests && python3 -m pytest -q)
  3. Review:  git -C "$PROD" status  &&  rtk proxy git -C "$PROD" diff
  4. Commit/push prod main only after explicit release approval.
     The mirror copies files only — beta's commit history does NOT cross over, so this
     becomes one fresh prod commit (or however many you choose to split it into).
EOF
fi
