#!/usr/bin/env bash
# Update librecoach/node-red.ref after a reviewed Node-RED commit is on origin/main.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BETA="$(cd "$SCRIPT_DIR/.." && pwd)"
NODE_RED_REPO="${NODE_RED_REPO:-$(cd "$BETA/.." && pwd)/librecoach-node-red}"
REF_FILE="$BETA/librecoach/node-red.ref"

[[ -d "$NODE_RED_REPO/.git" ]] || {
    echo "ERROR: Node-RED repository not found at $NODE_RED_REPO" >&2
    exit 1
}

if [[ -n "$(git -C "$NODE_RED_REPO" status --porcelain)" ]]; then
    echo "ERROR: Node-RED working tree is not clean: $NODE_RED_REPO" >&2
    exit 1
fi

git -C "$NODE_RED_REPO" fetch origin main
NODE_RED_REF="${1:-$(git -C "$NODE_RED_REPO" rev-parse HEAD)}"

[[ "$NODE_RED_REF" =~ ^[0-9a-f]{40}$ ]] || {
    echo "ERROR: expected a full lowercase 40-character commit SHA" >&2
    exit 1
}
git -C "$NODE_RED_REPO" cat-file -e "$NODE_RED_REF^{commit}"
git -C "$NODE_RED_REPO" merge-base --is-ancestor "$NODE_RED_REF" origin/main || {
    echo "ERROR: $NODE_RED_REF is not on origin/main" >&2
    exit 1
}
git -C "$NODE_RED_REPO" show "$NODE_RED_REF:artifact/flows.json" >/dev/null || {
    echo "ERROR: artifact/flows.json is absent from $NODE_RED_REF" >&2
    exit 1
}
git -C "$NODE_RED_REPO" show "$NODE_RED_REF:flows_cred.json" >/dev/null || {
    echo "ERROR: flows_cred.json is absent from $NODE_RED_REF" >&2
    exit 1
}

SRC_TIME="$(git -C "$NODE_RED_REPO" log -1 --format=%ct "$NODE_RED_REF" -- src/)"
ARTIFACT_TIME="$(git -C "$NODE_RED_REPO" log -1 --format=%ct "$NODE_RED_REF" -- artifact/)"
if [[ -n "$SRC_TIME" && ( -z "$ARTIFACT_TIME" || "$ARTIFACT_TIME" -lt "$SRC_TIME" ) ]]; then
    echo "ERROR: artifact/ is older than src/ at $NODE_RED_REF; deploy in Node-RED first" >&2
    exit 1
fi

printf '%s\n' "$NODE_RED_REF" > "$REF_FILE"
echo "Updated $REF_FILE to $NODE_RED_REF"
