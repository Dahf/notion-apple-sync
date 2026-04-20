#!/usr/bin/env bash
set -euo pipefail

# Build Tailwind CSS locally using the standalone CLI (no Node required).
# Downloads the binary into .bin/ on first run.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="${ROOT}/.bin"
CLI="${BIN_DIR}/tailwindcss"
TAILWIND_VERSION="v3.4.17"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "${OS}-${ARCH}" in
  linux-x86_64)  ASSET="tailwindcss-linux-x64" ;;
  linux-aarch64|linux-arm64) ASSET="tailwindcss-linux-arm64" ;;
  darwin-arm64)  ASSET="tailwindcss-macos-arm64" ;;
  darwin-x86_64) ASSET="tailwindcss-macos-x64" ;;
  mingw*|msys*|cygwin*|windows_nt*)
    ASSET="tailwindcss-windows-x64.exe"
    CLI="${BIN_DIR}/tailwindcss.exe"
    ;;
  *) echo "unsupported: ${OS}-${ARCH}" >&2; exit 1 ;;
esac

mkdir -p "${BIN_DIR}"
if [ ! -x "${CLI}" ]; then
  echo "Downloading Tailwind standalone CLI (${ASSET})..."
  curl -sSL -o "${CLI}" "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/${ASSET}"
  chmod +x "${CLI}"
fi

echo "Building app/static/css/app.css..."
"${CLI}" \
  -c "${ROOT}/tailwind.config.js" \
  -i "${ROOT}/app/static/css/tailwind.src.css" \
  -o "${ROOT}/app/static/css/app.css" \
  --minify

echo "Done. $(wc -c < "${ROOT}/app/static/css/app.css") bytes."
