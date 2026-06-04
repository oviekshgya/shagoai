#!/usr/bin/env bash
set -e

APP_NAME="shagoai"
REPO_URL="git+https://github.com/oviekshgya/ollama-agent.git"

CONFIG_DIR="$HOME/.config/shagoai"
CONFIG_FILE="$CONFIG_DIR/config.json"

DEFAULT_API_URL="${SHAGO_API_URL:-http://100.75.45.113:8184}"
DEFAULT_MODEL="${SHAGO_MODEL:-default}"

echo ""
echo "╭────────────────────────────────────────────╮"
echo "│              SHAGO AI INSTALL              │"
echo "╰────────────────────────────────────────────╯"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required."
  exit 1
fi

echo "Checking Python..."
python3 --version

echo ""
echo "Installing pipx if needed..."

python3 -m pip install --user --upgrade pipx >/dev/null 2>&1 || true
python3 -m pipx ensurepath >/dev/null 2>&1 || true

export PATH="$HOME/.local/bin:$PATH"

if ! command -v pipx >/dev/null 2>&1; then
  echo "pipx not found after install."
  echo "Fallback to pip --user..."
  python3 -m pip install --user --upgrade "$REPO_URL"
else
  echo "Installing SHAGO AI CLI..."
  pipx install --force "$REPO_URL"
fi

mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
  cat > "$CONFIG_FILE" <<EOF
{
  "api_url": "$DEFAULT_API_URL",
  "token": "",
  "model": "$DEFAULT_MODEL",
  "guard": "approval required",

  "rpk_enabled": true,
  "rpk_max_tool_chars": 16000,
  "rpk_max_read_file_chars": 24000,
  "rpk_max_command_chars": 14000,
  "rpk_max_search_chars": 12000,
  "rpk_max_diff_chars": 18000
}
EOF
fi

echo ""
echo "SHAGO AI installed."
echo ""
echo "Next:"
echo "  shagoai"
echo ""
echo "Config:"
echo "  $CONFIG_FILE"
echo ""

if ! command -v shagoai >/dev/null 2>&1; then
  echo "NOTE: shagoai command not found in current shell."
  echo "Run:"
  echo "  source ~/.bashrc"
  echo ""
  echo "Or open a new terminal."
fi