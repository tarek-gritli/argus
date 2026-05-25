#!/usr/bin/env bash
# Build a standalone argus binary for the current platform.
# Output: apps/cli/dist/argus
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building argus binary for $(uname -s)/$(uname -m)..."

uv sync --group build

uv run pyinstaller argus.spec --clean --noconfirm

echo ""
echo "Binary built: $SCRIPT_DIR/dist/argus"
echo "Size: $(du -sh dist/argus | cut -f1)"
