#!/bin/bash
set -euo pipefail

BASE_DIR="/Users/mario.lin/Documents/miniflux-ai"
CONFIG_PATH="$BASE_DIR/config.yml"
OUTPUT_PATH="$BASE_DIR/config.yml.b64"

base64 -b 0 -i "$CONFIG_PATH" -o "$OUTPUT_PATH"
