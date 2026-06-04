#!/usr/bin/env bash
set -euo pipefail

APP_NAME="shagoai"

REMOTE_USER="${SHAGO_RELEASE_USER:-shagya}"
REMOTE_HOST="${SHAGO_RELEASE_HOST:-100.75.45.113}"
REMOTE_DIR="${SHAGO_RELEASE_DIR:-/home/shagya/project/shagoai-server/releases}"

INSTALL_BASE="${SHAGO_INSTALL_BASE:-https://shagoai.shagya-tech.my.id}"
USE_SUDO="${SHAGO_REMOTE_SUDO:-0}"

echo ""
echo "╭────────────────────────────────────────────╮"
echo "│          SHAGO AI BUILD & RELEASE          │"
echo "╰────────────────────────────────────────────╯"
echo ""

if [ ! -f "pyproject.toml" ]; then
  echo "ERROR: run this script from shagoai project root."
  exit 1
fi

VERSION="$(
python - <<'PY'
import re
from pathlib import Path

init_file = Path("shagoai/__init__.py")
text = init_file.read_text(encoding="utf-8")
match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)

if not match:
    raise SystemExit("missing __version__ in shagoai/__init__.py")

print(match.group(1))
PY
)"

PYPROJECT_VERSION="$(
python - <<'PY'
import re
from pathlib import Path

text = Path("pyproject.toml").read_text(encoding="utf-8")
match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)

if not match:
    raise SystemExit("missing version in pyproject.toml")

print(match.group(1))
PY
)"

if [ "$VERSION" != "$PYPROJECT_VERSION" ]; then
  echo "ERROR: version mismatch"
  echo "  shagoai/__init__.py : $VERSION"
  echo "  pyproject.toml      : $PYPROJECT_VERSION"
  exit 1
fi

echo "Version: $VERSION"
echo ""

echo "Checking --version support in source..."
if ! grep -q -- "--version" shagoai/cli.py; then
  echo "ERROR: shagoai/cli.py does not contain --version support."
  echo "Add --version first, then rebuild."
  exit 1
fi

echo "Cleaning old build..."
rm -rf dist build shagoai.egg-info

echo "Installing build tool..."
python -m pip install -U build >/dev/null

echo "Building wheel..."
python -m build

WHEEL="dist/${APP_NAME}-${VERSION}-py3-none-any.whl"

if [ ! -f "$WHEEL" ]; then
  echo "ERROR: wheel not found: $WHEEL"
  echo "Available dist files:"
  ls -lh dist || true
  exit 1
fi

WHEEL_NAME="$(basename "$WHEEL")"

echo ""
echo "Built:"
ls -lh "$WHEEL"

echo ""
echo "Testing built wheel in isolated venv..."

TEST_VENV="$(mktemp -d)"
python -m venv "$TEST_VENV/venv"
"$TEST_VENV/venv/bin/python" -m pip install --upgrade pip >/dev/null
"$TEST_VENV/venv/bin/python" -m pip install "$WHEEL" >/dev/null

VERSION_OUTPUT="$("$TEST_VENV/venv/bin/shagoai" --version 2>&1 || true)"

echo "Version output:"
echo "$VERSION_OUTPUT"

if echo "$VERSION_OUTPUT" | grep -q "SHAGO//AGENT"; then
  echo "ERROR: shagoai --version opened banner."
  echo "Fix cli.py before release."
  rm -rf "$TEST_VENV"
  exit 1
fi

EXPECTED_OUTPUT="shagoai $VERSION"

if [ "$VERSION_OUTPUT" != "$EXPECTED_OUTPUT" ]; then
  echo "ERROR: invalid --version output"
  echo "Expected: $EXPECTED_OUTPUT"
  echo "Got     : $VERSION_OUTPUT"
  rm -rf "$TEST_VENV"
  exit 1
fi

rm -rf "$TEST_VENV"

echo "Wheel test passed."

echo ""
echo "Uploading to server:"
echo "  ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/${WHEEL_NAME}"
echo ""

scp "$WHEEL" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/${WHEEL_NAME}"

if [ "$USE_SUDO" = "1" ]; then
  ssh "${REMOTE_USER}@${REMOTE_HOST}" "
    sudo mkdir -p '${REMOTE_DIR}' &&
    sudo rm -f '${REMOTE_DIR}/shagoai-latest-py3-none-any.whl' &&
    sudo mv '/tmp/${WHEEL_NAME}' '${REMOTE_DIR}/${WHEEL_NAME}' &&
    sudo chown -R '${REMOTE_USER}:${REMOTE_USER}' '${REMOTE_DIR}' &&
    sudo chmod 644 '${REMOTE_DIR}/${WHEEL_NAME}' &&
    ls -lh '${REMOTE_DIR}'
  "
else
  ssh "${REMOTE_USER}@${REMOTE_HOST}" "
    mkdir -p '${REMOTE_DIR}' &&
    rm -f '${REMOTE_DIR}/shagoai-latest-py3-none-any.whl' &&
    mv '/tmp/${WHEEL_NAME}' '${REMOTE_DIR}/${WHEEL_NAME}' &&
    chmod 644 '${REMOTE_DIR}/${WHEEL_NAME}' &&
    ls -lh '${REMOTE_DIR}'
  "
fi

echo ""
echo "Testing installer package URL..."
curl -fsSL "${INSTALL_BASE}/install.sh" | grep PACKAGE_URL || true

echo ""
echo "Testing wheel download..."
curl -fsSL "${INSTALL_BASE}/releases/${WHEEL_NAME}" -o "/tmp/${WHEEL_NAME}"
ls -lh "/tmp/${WHEEL_NAME}"

echo ""
echo "Release uploaded successfully."
echo ""
echo "Install/update command:"
echo "  curl -fsSL ${INSTALL_BASE}/install.sh | sh"
echo ""
