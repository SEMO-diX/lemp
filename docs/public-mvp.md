# Public MVP

## Goal

Prove that a fresh user can use GitHub as durable LLM memory without depending on the author's private environment.

## Included

- LEMP v1.1 protocol baseline
- local reference runtime
- `lemp init`, `validate`, `sync`, and `status`
- synthetic memory template
- tests and CI
- ChatGPT + GitHub integration guidance
- explicit permission/trust-boundary documentation

## Not included yet

- the author's private memory history
- v1.2 Semantic Approval
- a guarantee that connector permissions are sandboxed by LEMP
- authoritative online verification of GitHub Actions attestation from the public CLI

## Release gate

The intended release gate is a fresh repository test:

1. initialize synthetic LEMP memory;
2. commit it;
3. establish a validated canonical checkpoint;
4. change candidate state without promoting it and confirm canonical sync remains isolated;
5. connect the repository to ChatGPT through GitHub;
6. from a new conversation, recover the prior durable decision and current state;
7. verify that missing required context fails closed.
