#!/usr/bin/env sh
# install.sh — Install the Argus CLI
# Usage: curl -fsSL https://raw.githubusercontent.com/tarek-gritli/argus/main/install.sh | sh
set -e

REPO="tarek-gritli/argus"
BINARY_NAME="argus"
INSTALL_DIR="/usr/local/bin"

# ── Detect platform ────────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Linux)  PLATFORM="linux" ;;
  Darwin) PLATFORM="darwin" ;;
  *)
    echo "Unsupported OS: $OS"
    echo "Please download a binary manually from: https://github.com/$REPO/releases"
    exit 1
    ;;
esac

case "$ARCH" in
  x86_64|amd64) ARCH_TAG="x86_64" ;;
  arm64|aarch64) ARCH_TAG="arm64" ;;
  *)
    echo "Unsupported architecture: $ARCH"
    echo "Please download a binary manually from: https://github.com/$REPO/releases"
    exit 1
    ;;
esac

ASSET_NAME="${BINARY_NAME}-${PLATFORM}-${ARCH_TAG}"

# ── Resolve latest release ─────────────────────────────────────────────────────
echo "Fetching latest Argus release..."
LATEST_URL="https://api.github.com/repos/${REPO}/releases/latest"

if command -v curl >/dev/null 2>&1; then
  RELEASE_JSON="$(curl -fsSL "$LATEST_URL")"
elif command -v wget >/dev/null 2>&1; then
  RELEASE_JSON="$(wget -qO- "$LATEST_URL")"
else
  echo "Error: curl or wget is required."
  exit 1
fi

DOWNLOAD_URL="$(echo "$RELEASE_JSON" | grep -o "\"browser_download_url\": \"[^\"]*${ASSET_NAME}\"" | head -1 | cut -d'"' -f4)"

if [ -z "$DOWNLOAD_URL" ]; then
  echo "Error: could not find asset '${ASSET_NAME}' in the latest release."
  echo "Available at: https://github.com/$REPO/releases"
  exit 1
fi

# ── Download ───────────────────────────────────────────────────────────────────
TMP="$(mktemp)"
CHECKSUMS_TMP="$(mktemp)"
echo "Downloading ${ASSET_NAME}..."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$DOWNLOAD_URL" -o "$TMP"
  CHECKSUMS_URL="$(echo "$RELEASE_JSON" | grep -o "\"browser_download_url\": \"[^\"]*checksums\.txt\"" | head -1 | cut -d'"' -f4)"
  [ -n "$CHECKSUMS_URL" ] && curl -fsSL "$CHECKSUMS_URL" -o "$CHECKSUMS_TMP"
else
  wget -qO "$TMP" "$DOWNLOAD_URL"
  CHECKSUMS_URL="$(echo "$RELEASE_JSON" | grep -o "\"browser_download_url\": \"[^\"]*checksums\.txt\"" | head -1 | cut -d'"' -f4)"
  [ -n "$CHECKSUMS_URL" ] && wget -qO "$CHECKSUMS_TMP" "$CHECKSUMS_URL"
fi

# ── Verify checksum ────────────────────────────────────────────────────────────
if [ -s "$CHECKSUMS_TMP" ]; then
  echo "Verifying checksum..."
  EXPECTED="$(grep " ${ASSET_NAME}$" "$CHECKSUMS_TMP" | awk '{print $1}')"
  if [ -z "$EXPECTED" ]; then
    echo "Error: no checksum entry for '${ASSET_NAME}' in checksums.txt"
    rm -f "$TMP" "$CHECKSUMS_TMP"
    exit 1
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL="$(sha256sum "$TMP" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    ACTUAL="$(shasum -a 256 "$TMP" | awk '{print $1}')"
  else
    echo "Error: neither sha256sum nor shasum found; cannot verify binary integrity."
    rm -f "$TMP" "$CHECKSUMS_TMP"
    exit 1
  fi
  if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "Error: checksum mismatch for '${ASSET_NAME}'"
    echo "  expected: $EXPECTED"
    echo "  actual:   $ACTUAL"
    rm -f "$TMP" "$CHECKSUMS_TMP"
    exit 1
  fi
  echo "Checksum verified."
else
  echo "Warning: checksums.txt not found in release; skipping integrity check."
fi
rm -f "$CHECKSUMS_TMP"

chmod +x "$TMP"

# ── Install ────────────────────────────────────────────────────────────────────
if [ -w "$INSTALL_DIR" ]; then
  mv "$TMP" "${INSTALL_DIR}/${BINARY_NAME}"
elif command -v sudo >/dev/null 2>&1; then
  echo "Installing to ${INSTALL_DIR} (requires sudo)..."
  sudo mv "$TMP" "${INSTALL_DIR}/${BINARY_NAME}"
else
  INSTALL_DIR="$HOME/.local/bin"
  mkdir -p "$INSTALL_DIR"
  mv "$TMP" "${INSTALL_DIR}/${BINARY_NAME}"
  echo "Installed to ${INSTALL_DIR}/${BINARY_NAME}"
  echo "Make sure ${INSTALL_DIR} is in your PATH."
fi

# ── Verify ─────────────────────────────────────────────────────────────────────
echo ""
if "${INSTALL_DIR}/${BINARY_NAME}" --help >/dev/null 2>&1; then
  VERSION="$("${INSTALL_DIR}/${BINARY_NAME}" --version 2>/dev/null || echo "installed")"
  echo "Argus CLI installed successfully ($VERSION)"
  echo ""
  echo "  Set ARGUS_GATEWAY_URL to point at your Argus backend (defaults to localhost:8000):"
  echo "    export ARGUS_GATEWAY_URL=https://your-gateway-url"
  echo ""
  echo "  Get started:"
  echo "    argus login"
  echo "    argus review"
else
  echo "Warning: binary installed but --help failed. Check ${INSTALL_DIR}/${BINARY_NAME}"
fi
