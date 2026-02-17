#!/bin/bash
# Node-RED initialization script for LibreCoach (PRESERVE FLOWS MODE)
# This script runs inside the Node-RED container on startup via init_commands
#
# DIFFERENCE FROM STANDARD SCRIPT:
# This version DOES NOT copy flows.json or flows_cred.json.
# It only updates reference files and dependencies.

set -e

PROJECT_DIR="/config/projects/librecoach-node-red"
SOURCE_DIR="/share/.librecoach"

echo "LibreCoach: Running in PRESERVE FLOWS mode."
echo "   - Updating RVC decoders..."
echo "   - Updating package.json..."
echo "   - SKIPPING flows.json (User flows preserved)"

# Create project directories
mkdir -p "$PROJECT_DIR/data"

# Copy RVC decoder data
cp -r "$SOURCE_DIR/data/." "$PROJECT_DIR/data/"

# Copy package.json to config directory for Node-RED dependencies
cp "$SOURCE_DIR/package.json" /config/package.json

# Copy settings.js to Node-RED config
cp "$SOURCE_DIR/data/settings.js" /config/settings.js

# Keep GPL license with the installed project
if [ -f "$SOURCE_DIR/LICENSE" ]; then
  cp "$SOURCE_DIR/LICENSE" "$PROJECT_DIR/LICENSE"
fi

# DO NOT COPY flows.json or flows_cred.json
# existing flows are preserved.

echo "LibreCoach Node-RED initialization (Preserve Mode) complete"
