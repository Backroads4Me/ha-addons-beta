#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
RUN_SH="$SCRIPT_DIR/../run.sh"
TEST_TMP=$(mktemp -d)
trap 'rm -rf -- "$TEST_TMP"' EXIT

load_function() {
	local name=$1
	local definition
	definition=$(sed -n "/^\t${name}() {/,/^\t}/p" "$RUN_SH")
	if [ -z "$definition" ]; then
		echo "Function not found: $name" >&2
		exit 1
	fi
	eval "$definition"
}

assert_status() {
	local expected=$1
	shift
	local actual
	set +e
	"$@"
	actual=$?
	set -e
	if [ "$actual" -ne "$expected" ]; then
		echo "Expected status $expected, got $actual from: $*" >&2
		exit 1
	fi
}

load_function get_addon_install_state
load_function classify_nodered_install_state
load_function mark_nodered_install_pending
load_function is_nodered_install_pending
load_function clear_nodered_install_pending
load_function mark_nodered_managed

api_call() {
	printf '%s\n' "$MOCK_API_RESPONSE"
}

log_debug() {
	:
}

bashio::log.info() {
	:
}

redact_json() {
	printf '%s\n' "$1"
}

SLUG_NODERED="a0d7b954_nodered"
export DATA_DIR="$TEST_TMP"
NODERED_INSTALL_PENDING_FILE="$TEST_TMP/install-pending.json"
STATE_FILE="$TEST_TMP/state.json"
export ADDON_VERSION="test-version"
export PREVENT_FLOW_UPDATES=false

MOCK_API_RESPONSE='{"result":"ok","data":{"installed":true}}'
assert_status 0 get_addon_install_state "$SLUG_NODERED"

MOCK_API_RESPONSE='{"result":"ok","data":{"installed":false}}'
assert_status 1 get_addon_install_state "$SLUG_NODERED"

MOCK_API_RESPONSE='{"result":"error","message":"Supervisor unavailable"}'
assert_status 2 get_addon_install_state "$SLUG_NODERED"

test "$(classify_nodered_install_state 0 true false)" = "managed"
test "$(classify_nodered_install_state 0 false true)" = "resume"
test "$(classify_nodered_install_state 0 false false)" = "preexisting"
test "$(classify_nodered_install_state 1 false true)" = "install"
test "$(classify_nodered_install_state 2 false false)" = "unknown"

mark_nodered_install_pending
assert_status 0 is_nodered_install_pending
jq -e --arg slug "$SLUG_NODERED" \
	'.owner == "librecoach" and .slug == $slug and .version == "test-version"' \
	"$NODERED_INSTALL_PENDING_FILE" >/dev/null

mark_nodered_managed "test-flow-hash"
jq -e \
	'.nodered_managed == true and .flows_hash == "test-flow-hash" and .prevent_flow_updates == false' \
	"$STATE_FILE" >/dev/null
test ! -e "$NODERED_INSTALL_PENDING_FILE"
test ! -e "${STATE_FILE}.tmp"

echo "orchestrator state tests passed"
