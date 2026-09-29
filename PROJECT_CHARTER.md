# Project Charter

## Purpose

LEMP provides a reproducible way to use GitHub as durable external memory for LLMs. The reference path is ChatGPT using its GitHub integration as memory I/O while LEMP supplies deterministic structure, canonical checkpoint selection, integrity validation, and cross-session recovery rules.

## Public repository boundary

This repository is a clean public implementation. It is not a mirror of the author's private memory repository and must not receive private sessions, events, archives, state, or historical memory.

## Public MVP scope

The first public MVP targets LEMP v1.1, a ChatGPT + GitHub reference integration, synthetic-only example memory, a local reference runtime, CI, and a fresh-repository recovery demonstration.

The proposed Semantic Approval & Authority Separation work is future protocol work and is not a prerequisite for the first public release.

## Completion condition

A third party should be able to create a fresh repository from the synthetic template, establish a canonical checkpoint, connect it to ChatGPT through GitHub, and recover the required prior context in a new conversation without depending on the author's private repository.

## Decision criteria

Public-release readiness is judged by reproducibility, separation of implementation from private instance data, security/trust-boundary clarity, and ease of understanding.

## Open decisions

The repository uses Apache License 2.0. Final first-release checkpoint/write-back packaging is still intentionally open.
