#!/bin/bash
# Node-RED initialization script for LibreCoach (PRESERVE FLOWS MODE)
# This script runs inside the Node-RED container on startup via init_commands
#
# DIFFERENCE FROM STANDARD SCRIPT:
# This version DOES NOT copy flows.json or flows_cred.json.
# It only updates reference files and dependencies.

set -e

# Robust Suicide Check: Exit if LibreCoach is gone
OWNER_SLUG="REPLACE_ME" # Injected by run.sh to handle both beta and prod
SOURCE_DIR="/share/.librecoach"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "LibreCoach source directory not found. Exiting."
    exit 0
fi

# Multi-retry check against Supervisor API to handle transient startup errors
MAX_RETRIES=3
for i in $(seq 1 $MAX_RETRIES); do
    # Get both body and status code. --max-time 3 allows for busy supervisor during boot.
    RESPONSE=$(curl -s -m 3 -H "Authorization: Bearer $SUPERVISOR_TOKEN" -w "\n%{http_code}" http://supervisor/addons/$OWNER_SLUG/info || echo -e "\n000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        # Check JSON for installed=true or state=started
        BODY_NOSPACE=$(echo "$BODY" | tr -d ' ' | tr -d '\n' | tr -d '\r')
        if echo "$BODY_NOSPACE" | grep -q '"installed":true' || echo "$BODY_NOSPACE" | grep -q '"state":"started"'; then
            echo "LibreCoach ($OWNER_SLUG) is verified installed."
            break
        else
            echo "LibreCoach ($OWNER_SLUG) exists but is not installed. Skipping."
            exit 0
        fi
    elif [ "$HTTP_CODE" = "404" ]; then
        echo "LibreCoach ($OWNER_SLUG) not found. Skipping initialization."
        exit 0
    else
        echo "Supervisor busy or error $HTTP_CODE (Attempt $i/$MAX_RETRIES). Retrying..."
        if [ $i -lt $MAX_RETRIES ]; then
            sleep 2
        else
            echo "Max retries reached. Unable to confirm LibreCoach status. Assuming NOT installed for safety."
            exit 0
        fi
    fi
done

PROJECT_DIR="/config/projects/librecoach-node-red"

echo "LibreCoach: Running in PRESERVE FLOWS mode."
echo "   - Updating decodata files..."
echo "   - SKIPPING flows.json (User flows preserved)"

# Create project directories
mkdir -p "$PROJECT_DIR/data"

# Copy RVC decoder data
cp -r "$SOURCE_DIR/data/." "$PROJECT_DIR/data/"

# Deploy settings.js even in preserve mode. It is LibreCoach-managed runtime
# config (context storage location, env injection) — not user flow content — so
# preserving flows must not freeze it. Required for the persistent context dir.
cp "$SOURCE_DIR/data/settings.js" /config/settings.js

# Developer override: when this install is flagged as a dev environment, enable
# Node-RED projects. Canonical settings.js ships projects disabled for end users.
# A maintainer drops an empty sentinel file at the path below (in their own
# /share, never committed to the repo) to mark the install as a dev environment;
# additional dev-only behaviors can gate on the same marker in future.
if [ -f "$SOURCE_DIR/.librecoach-dev" ]; then
    node -e '
        const fs = require("fs");
        const p = "/config/settings.js";
        let s = fs.readFileSync(p, "utf8");
        const patched = s.replace(/projects:\s*\{\s*enabled:\s*false/, "projects: { enabled: true");
        if (patched !== s) { fs.writeFileSync(p, patched); process.exit(0); }
        process.exit(1);
    ' 2>/dev/null \
        && echo "LibreCoach: Node-RED projects ENABLED (developer sentinel present)" \
        || echo "LibreCoach: projects sentinel present but settings.js already had projects enabled or pattern not found"
fi

# Migrate persistent context keys from the old default location (/config/context)
# to the new explicit location (/share/.librecoach/context), which survives add-on
# reinstalls. Only fills in keys absent from the destination — never overwrites.
node -e '
  const fs = require("fs");
  const OLD = "/config/context/global/global.json";
  const NEW_DIR = "/share/.librecoach/context/global";
  const NEW = NEW_DIR + "/global.json";
  const KEYS = [
    "rv_manufacturer", "rv_model", "rv_year", "rv_other",
    "victronPortalId",
    "dimmableLights", "dimmableAcLoads", "dimmableIndicators",
    "dcDimmerStatusBackedInstances", "floorHeatLevelMap"
  ];

  if (!fs.existsSync(OLD)) process.exit(0);

  let oldCtx;
  try { oldCtx = JSON.parse(fs.readFileSync(OLD, "utf8")); }
  catch (e) { process.exit(0); }

  const toMigrate = {};
  for (const k of KEYS) {
    if (oldCtx[k] !== undefined) toMigrate[k] = oldCtx[k];
  }
  if (Object.keys(toMigrate).length === 0) process.exit(0);

  fs.mkdirSync(NEW_DIR, { recursive: true });

  let newCtx = {};
  if (fs.existsSync(NEW)) {
    try { newCtx = JSON.parse(fs.readFileSync(NEW, "utf8")); } catch (e) {}
  }

  let count = 0;
  for (const [k, v] of Object.entries(toMigrate)) {
    if (newCtx[k] === undefined) { newCtx[k] = v; count++; }
  }

  if (count > 0) {
    fs.writeFileSync(NEW, JSON.stringify(newCtx, null, 4));
    console.log("LibreCoach: Migrated " + count + " context key(s) to /share/.librecoach/context/");
  }
' 2>/dev/null || echo "LibreCoach: Context migration skipped"

echo "LibreCoach Node-RED initialization (Preserve Mode) complete"
