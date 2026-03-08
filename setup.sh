#!/usr/bin/env bash
set -euo pipefail

if ! command -v go >/dev/null 2>&1; then
  if [ -x "$HOME/.local/go1.26.1/bin/go" ]; then
    export PATH="$HOME/.local/go1.26.1/bin:$PATH"
  else
    echo "Go toolchain not found. Install Go 1.26+ or place it at $HOME/.local/go1.26.1/bin/go" >&2
    exit 1
  fi
fi

go version
go mod download
