from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .runtime import LEMPError, format_payload, init_memory, status, sync, validate


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lemp", description="LEMP public reference runtime")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a synthetic LEMP memory repository")
    init.add_argument("directory")

    val = sub.add_parser("validate", help="validate a memory working tree")
    val.add_argument("--root", default=".")
    val.add_argument("--format", choices=["text", "json"], default="text")

    for name in ("sync", "status"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--root", default=".")
        cmd.add_argument("--format", choices=["text", "json"], default="text")
        cmd.add_argument("--no-fetch-tags", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            path = init_memory(Path(args.directory))
            print(f"Initialized synthetic LEMP memory at {path}")
            return 0
        if args.command == "validate":
            result = validate(Path(args.root))
            payload = result.as_dict()
            print(format_payload(payload, args.format))
            return 0 if result.integrity != "FAIL" else 1
        if args.command == "sync":
            payload = sync(Path(args.root), fetch_tags=not args.no_fetch_tags)
            print(format_payload(payload, args.format))
            return 0
        if args.command == "status":
            payload = status(Path(args.root), fetch_tags=not args.no_fetch_tags)
            print(format_payload(payload, args.format))
            return 0
    except LEMPError as exc:
        print(f"LEMP FAIL: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
