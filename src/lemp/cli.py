from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .promotion import PromotionError, prepare_tag, prepare_tag_from_environment
from .runtime import LEMPError, checkpoint, format_payload, init_memory, status, sync, validate


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lemp", description="LEMP public reference runtime")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a synthetic LEMP memory repository")
    init.add_argument("directory")

    val = sub.add_parser("validate", help="validate a memory working tree")
    val.add_argument("--root", default=".")
    val.add_argument("--format", choices=["text", "json"], default="text")

    promote = sub.add_parser(
        "prepare-tag",
        help="prepare an attested canonical tag for the current GitHub Actions run",
    )
    promote.add_argument("--root", default=".")
    promote.add_argument("--format", choices=["text", "json"], default="json")
    promote.add_argument("--checkpoint")
    promote.add_argument("--commit-sha")
    promote.add_argument("--repository")
    promote.add_argument("--run-id")
    promote.add_argument("--run-attempt")
    promote.add_argument("--event")

    cp = sub.add_parser("checkpoint", help="finalize a prepared candidate checkpoint")
    cp.add_argument("--root", default=".")
    cp.add_argument("--format", choices=["text", "json"], default="text")
    cp.add_argument("--no-fetch-tags", action="store_true")
    cp.add_argument("--allow-main", action="store_true")
    cp.add_argument("--check-only", action="store_true")
    cp.add_argument("--message")
    cp.add_argument("--offline-attestation", action="store_true")

    for name in ("sync", "status"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--root", default=".")
        cmd.add_argument("--format", choices=["text", "json"], default="text")
        cmd.add_argument("--no-fetch-tags", action="store_true")
        cmd.add_argument("--offline-attestation", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            path = init_memory(Path(args.directory))
            print(f"Initialized synthetic LEMP memory at {path}")
            return 0
        if args.command == "prepare-tag":
            explicit = any(
                value is not None
                for value in (
                    args.checkpoint,
                    args.commit_sha,
                    args.repository,
                    args.run_id,
                    args.run_attempt,
                    args.event,
                )
            )
            if explicit:
                import os
                import yaml

                manifest = yaml.safe_load(
                    (Path(args.root) / "MANIFEST.yaml").read_text(encoding="utf-8")
                ) or {}
                payload = prepare_tag(
                    Path(args.root),
                    checkpoint=args.checkpoint or str(manifest.get("checkpoint") or ""),
                    commit_sha=args.commit_sha or os.environ.get("GITHUB_SHA", ""),
                    repository=args.repository or os.environ.get("GITHUB_REPOSITORY", ""),
                    run_id=args.run_id or os.environ.get("GITHUB_RUN_ID", ""),
                    run_attempt=args.run_attempt or os.environ.get("GITHUB_RUN_ATTEMPT", ""),
                    event=args.event or os.environ.get("GITHUB_EVENT_NAME", ""),
                )
            else:
                payload = prepare_tag_from_environment(Path(args.root))
            print(format_payload(payload, args.format))
            return 0
        if args.command == "validate":
            result = validate(Path(args.root))
            payload = result.as_dict()
            print(format_payload(payload, args.format))
            return 0 if result.integrity != "FAIL" else 1
        if args.command == "sync":
            payload = sync(
                Path(args.root),
                fetch_tags=not args.no_fetch_tags,
                offline_attestation=args.offline_attestation,
            )
            print(format_payload(payload, args.format))
            return 0
        if args.command == "checkpoint":
            payload = checkpoint(
                Path(args.root),
                fetch_tags=not args.no_fetch_tags,
                allow_main=args.allow_main,
                check_only=args.check_only,
                commit_message=args.message,
                offline_attestation=args.offline_attestation,
            )
            print(format_payload(payload, args.format))
            return 0
        if args.command == "status":
            payload = status(
                Path(args.root),
                fetch_tags=not args.no_fetch_tags,
                offline_attestation=args.offline_attestation,
            )
            print(format_payload(payload, args.format))
            return 0
    except (LEMPError, PromotionError) as exc:
        print(f"LEMP FAIL: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
