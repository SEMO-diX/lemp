# ChatGPT + GitHub reference integration

The practical reference deployment uses ChatGPT's GitHub integration as the memory I/O path.

## Intended flow

1. Create a dedicated private GitHub repository for memory.
2. Initialize it from the synthetic LEMP template.
3. Commit the files and establish a canonical `lemp-valid/CPxxxxxx` checkpoint.
4. Connect GitHub to ChatGPT.
5. In ChatGPT, request `memory sync` and point it to the memory repository if needed.
6. ChatGPT reads `BOOTSTRAP.md`, resolves the canonical checkpoint, loads the declared required context, and reports integrity.
7. In a fresh conversation, repeat `memory sync` to recover durable context.

## Permissions

GitHub permissions are not controlled by LEMP.

For synchronization, prefer the lowest permission level that lets ChatGPT read the memory repository. Write-back requires write authority and therefore expands the trust boundary. A setting that allows all actions without confirmation is a convenience choice, not a LEMP requirement.

Because ChatGPT and GitHub product controls may change, this repository documents the architectural rule (least privilege) rather than claiming a permanent UI label or exact permission matrix.

## What LEMP protects

LEMP is designed to keep unvalidated candidate state from silently becoming canonical memory, to detect missing required context, and to preserve a source-recovery path.

It does not make a broadly privileged GitHub connector harmless. Repository access control, account security, branch/ruleset settings, and external backups remain separate controls.


## Canonical promotion

The generated synthetic memory repository includes `.github/workflows/lemp-canonical.yml`. On a validated push to `main`, it checks checkpoint sequencing, runs a pinned Gitleaks history scan, prepares an annotated `lemp-valid/CPxxxxxx` tag bound to the exact commit and workflow run/attempt, and pushes that tag.

The preview workflow installs the public runtime from an immutable verified commit SHA rather than a mutable branch. The first tagged software release should replace that preview commit pin with the corresponding immutable release tag.


## Runtime source portability

`lemp init` renders the generated Canonical Gate with an immutable verified reference-runtime commit by default. A fork or alternate distribution can supply `--runtime-spec` to render another pip-compatible immutable source without editing the generated workflow by hand.
