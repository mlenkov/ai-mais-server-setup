#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
GRAPHIFY="${GRAPHIFY:-$HOME/.local/bin/graphify}"
EXPORT_SCRIPT="${HERMES_HOME}/scripts/export-hermes-corpus.py"
OUT_DIR="${HERMES_HOME}/graphify-out"

export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-}"
export OPENAI_MODEL="${OPENAI_MODEL:-opencode-zen/deepseek-v4-flash-free}"

echo "=== Step 1: Export corpus from Hermes databases ==="
python3 "$EXPORT_SCRIPT"

echo ""
echo "=== Step 2: Check if semantic extraction is possible ==="
API_OK=0
if [ -n "$OPENAI_API_KEY" ]; then
  if curl -sf -X POST "$OPENAI_BASE_URL/chat/completions" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$OPENAI_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":5}" > /dev/null 2>&1; then
    API_OK=1
    echo "API key works — will do semantic extraction on corpus"
  else
    echo "API key rate-limited — skipping semantic, code-only update"
  fi
fi

echo ""
echo "=== Step 3: Update knowledge graph ==="
if [ "$API_OK" = "1" ]; then
  echo "Full update with corpus (AST + semantic)..."
  "$GRAPHIFY" update "$HERMES_HOME/graphify-corpus" --force --no-viz
else
  echo "Code-only update (AST)..."
  "$GRAPHIFY" update "$HERMES_HOME/hermes-agent" --force --no-viz
fi

echo ""
echo "=== Done ==="
echo "Graph: $OUT_DIR/graph.json"
