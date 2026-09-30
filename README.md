# LEMP

**GitHub-backed persistent memory for LLMs.**

LEMP (Long-term External Memory Protocol) treats a GitHub repository as durable external memory and verifies the memory state before an LLM relies on it.

The reference integration is **ChatGPT + GitHub**: ChatGPT uses its GitHub integration as the memory I/O path, while LEMP defines how durable context is structured, validated, checkpointed, and recovered across conversations.

> Status: public MVP reference flow proven end to end. The protocol baseline is LEMP v1.1. The private development memory and its Git history are intentionally not part of this repository.

## Why

Conversation context is temporary. A model may lose earlier details, and a claim that it “remembers” is not a durable source of truth.

LEMP moves durable context into GitHub and separates:

- candidate state from validated canonical memory;
- current state from historical records;
- required context from optional context;
- machine validation from model recollection.

## 5-minute local structural demo

```bash
python -m pip install -e .
lemp init demo-memory
cd demo-memory
git init -b main
git add .
git commit -m "Initialize synthetic LEMP memory"
lemp validate --format json
```

This local demo validates the synthetic repository structure only. **Do not create `lemp-valid/CPxxxxxx` tags manually.** Every canonical checkpoint, including CP000001, requires an annotated Canonical Gate attestation.

For authoritative `lemp sync`, push the generated memory repository to GitHub, allow the included `.github/workflows/lemp-canonical.yml` workflow to promote CP000001, fetch the resulting tag, and then run `lemp sync`. Normal synchronization remotely verifies the exact attested GitHub Actions run/attempt. `--offline-attestation` is diagnostic-only and is not canonical authority.

## ChatGPT + GitHub

For the intended reference flow, create a **dedicated private memory repository**, place a LEMP memory instance in it, connect GitHub to ChatGPT, and ask ChatGPT to perform `memory sync` by following the repository's `BOOTSTRAP.md`.

The GitHub integration's permission model remains a separate trust boundary. LEMP does **not** sandbox permissions granted to ChatGPT. See [docs/chatgpt-github.md](docs/chatgpt-github.md).

## Public / private boundary

This repository contains the protocol, reference runtime, synthetic templates, tests, and documentation.

It does **not** contain the author's real sessions, events, archives, current state, or private memory history. The public repository was created with a clean history rather than by making the private memory repository public.

## Implementation status

The public preview currently has a working Python package, synthetic template generation, snapshot-pinned `sync`, candidate/canonical `status`, candidate `checkpoint` finalization, Context Contract and Applicability schema validation, Decision-to-Contract coverage checks, provenance and archive coverage validation, annotated canonical-tag promotion, exact GitHub Actions run/attempt attestation verification, a generated Canonical Gate workflow with pinned Gitleaks scanning, and GitHub Actions CI.

The generated Canonical Gate also performs previous-generation compatibility checks and installs the public runtime from an immutable verified commit SHA by default. `lemp init --runtime-spec` can point forks or alternate distributions at another runtime source. A fresh private GitHub repository plus fresh ChatGPT conversations have now completed the intended MVP E2E proof, including remote attestation and unvalidated-candidate isolation. The next release step is the first tagged software release.

## Current commands

```text
lemp init <directory> [--runtime-spec <pip-spec>]
lemp validate [--root <directory>]
lemp sync [--root <directory>] [--format text|json]
lemp status [--root <directory>] [--format text|json]
lemp checkpoint [--root <directory>] [--check-only]
lemp prepare-tag [--root <directory>] [--format text|json]
```

Checkpoint finalization and exact remote workflow-attestation verification are implemented. Malformed repository inputs fail closed as structured validation errors, and the declared Python floor is exercised on Python 3.11 and 3.12 in CI. The fresh-repository/fresh-conversation ChatGPT + GitHub E2E has passed.

## Project documents

- [Project charter](PROJECT_CHARTER.md)
- [Public MVP](docs/public-mvp.md)
- [Architecture](docs/architecture.md)
- [ChatGPT + GitHub integration and permissions](docs/chatgpt-github.md)
- [Fresh repository / fresh chat E2E report](docs/E2E-REPORT.md)
- [Protocol v1.1](docs/protocol-v1.1.md)
- [Security](SECURITY.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
