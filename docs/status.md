# Implementation status

Updated: 2026-09-29

## Current verified state

Public implementation main SHA:

`2259e4a331d444ec7dc94c866f0475fa7d4d4536`

GitHub Actions Public LEMP CI Run #71 completed successfully for that SHA.

## Implemented

- clean public repository separated from private memory history
- Apache-2.0 license
- LEMP v1.1 public protocol baseline
- Python package and `lemp` CLI
- synthetic-only `lemp init`
- configurable runtime source with immutable verified default pin
- `validate`, `sync`, `status`, and candidate `checkpoint`
- canonical snapshot SHA pinning and candidate/canonical separation
- Context Contract JSON Schema validation
- Applicability JSON Schema and routing validation
- Decision-to-Contract coverage checks
- durable provenance validation
- source-recovery archive coverage validation
- previous-generation compatibility validation
- annotated canonical tag preparation and same-commit failed-attempt recovery
- CP000017+ exact GitHub Actions run/attempt attestation verification
- generated Canonical Gate workflow
- pinned Gitleaks repository-history scan in the generated Canonical Gate
- full local two-checkpoint lifecycle regression
- negative-path tests for schema, coverage, provenance, archive, path boundaries, attestation, and previous-generation constraints

## Remaining release proof

The major remaining proof is an external end-to-end run using a fresh GitHub memory repository and a fresh ChatGPT conversation:

1. initialize a new memory repository with `lemp init`;
2. allow its Canonical Gate to establish the first validated checkpoint;
3. connect that repository to ChatGPT through GitHub with least-privilege permissions;
4. perform `memory sync`;
5. start a fresh conversation and repeat `memory sync`;
6. verify that the synthetic durable decision and state are recovered from the validated canonical snapshot;
7. verify that a newer unvalidated candidate does not contaminate recovered memory.

After that proof, the preview runtime commit pin can be replaced by the first tagged software release.
