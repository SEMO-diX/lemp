# LEMP

**GitHub-backed persistent memory for LLMs.**

LEMP (Long-term External Memory Protocol) treats a GitHub repository as durable external memory and verifies the memory state before an LLM relies on it.

The reference integration is **ChatGPT + GitHub**: ChatGPT uses its GitHub integration as the memory I/O path, while LEMP defines how durable context is structured, validated, checkpointed, and recovered across conversations.

> Status: public MVP implementation in progress. The protocol baseline is LEMP v1.1. The private development memory and its Git history are intentionally not part of this repository.

## Why

Conversation context is temporary. A model may lose earlier details, and a claim that it “remembers” is not a durable source of truth.

LEMP moves durable context into GitHub and separates:

- candidate state from validated canonical memory;
- current state from historical records;
- required context from optional context;
- machine validation from model recollection.

## 5-minute local demo

```bash
python -m pip install -e .
lemp init demo-memory
cd demo-memory
git init -b main
git add .
git commit -m "Initialize synthetic LEMP memory"
git tag lemp-valid/CP000001
lemp validate
lemp sync
```

`lemp sync` resolves the newest valid canonical checkpoint, pins one commit SHA, validates required context, and returns the materialized working context.

## ChatGPT + GitHub

For the intended reference flow, create a **dedicated private memory repository**, place a LEMP memory instance in it, connect GitHub to ChatGPT, and ask ChatGPT to perform `memory sync` by following the repository's `BOOTSTRAP.md`.

The GitHub integration's permission model remains a separate trust boundary. LEMP does **not** sandbox permissions granted to ChatGPT. See [docs/chatgpt-github.md](docs/chatgpt-github.md).

## Public / private boundary

This repository contains the protocol, reference runtime, synthetic templates, tests, and documentation.

It does **not** contain the author's real sessions, events, archives, current state, or private memory history. The public repository was created with a clean history rather than by making the private memory repository public.

## Implementation status

The public preview currently has a working Python package, synthetic template generation, local canonical-tag resolution, snapshot-pinned `sync`, candidate/canonical `status`, structural validation, and GitHub Actions CI.

The next pre-release work is checkpoint finalization, the full canonical-promotion workflow, authoritative remote workflow-attestation verification, and a real fresh-conversation ChatGPT/GitHub E2E run.

## Current commands

```text
lemp init <directory>
lemp validate [--root <directory>]
lemp sync [--root <directory>] [--format text|json]
lemp status [--root <directory>] [--format text|json]
```

The current public preview deliberately starts with the read/sync path. Checkpoint finalization and full remote workflow-attestation verification will be added before the first tagged release.

## Project documents

- [Project charter](PROJECT_CHARTER.md)
- [Public MVP](docs/public-mvp.md)
- [Architecture](docs/architecture.md)
- [ChatGPT + GitHub integration and permissions](docs/chatgpt-github.md)
- [Protocol v1.1](docs/protocol-v1.1.md)
- [Security](SECURITY.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
