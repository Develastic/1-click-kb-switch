from __future__ import annotations

import argparse

from one_click_kb_switch.app import main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="1-Click-KB-Switch")
    parser.add_argument("--debug", action="store_true", help="Enable verbose console diagnostics")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(main(debug=args.debug))
