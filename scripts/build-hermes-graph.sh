#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
GRAPHIFY="${GRAPHIFY:-$HOME/.local/bin/graphify}"
EXPORT_SCRIPT="${HERMES_HOME}/scripts/export-hermes-corpus.py"

# Load API keys from Hermes .env
[ -f "$HERMES_HOME/.env" ] && source "$HERMES_HOME/.env"

export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-}"
export OPENAI_MODEL="${OPENAI_MODEL:-opencode-zen/deepseek-v4-flash-free}"

echo "=== Step 1: Export corpus (memories, conversations, configs) ==="
python3 "$EXPORT_SCRIPT"

echo ""
echo "=== Step 2: Incremental graph update (changed files only) ==="
"$GRAPHIFY" update "$HERMES_HOME/graphify-corpus" --force --no-viz

echo ""
echo "=== Step 3: Reload MCP server ==="
sudo systemctl restart hermes-graphify-mcp.service

echo ""
echo "=== Done ==="
echo "Graph: $HERMES_HOME/graphify-out/graph.json"
