#!/usr/bin/env bash
set -euo pipefail

if ! command -v cargo >/dev/null 2>&1; then
  if [ -x "$HOME/.cargo/bin/cargo" ]; then
    export PATH="$HOME/.cargo/bin:$PATH"
  else
    echo "Rust toolchain not found. Install rustup or cargo first." >&2
    exit 1
  fi
fi

cargo --version
cargo fetch --locked || cargo fetch
