# Implementation status

Updated: 2026-09-30

## Release-hardening state

The public implementation is in release-candidate hardening. Public CI covers Python 3.11 and 3.12, and both versions are required to remain green for release changes.

## Implemented

- clean public repository separated from private memory history
- Apache-2.0 license
- LEMP v1.1 public protocol baseline
- Python package and `lemp` CLI
- synthetic-only `lemp init`
- configurable runtime source with immutable verified default pin
- `validate`, `sync`, `status`, candidate `checkpoint`, and canonical-tag preparation
- canonical snapshot SHA pinning and candidate/canonical separation
- canonical attestation required from CP000001
- exact GitHub Actions run/attempt verification for normal canonical authority
- diagnostic-only, non-authoritative offline attestation mode
- Context Contract JSON Schema validation
- Applicability JSON Schema and routing validation
- Decision-to-Contract coverage checks
- malformed repository inputs normalized into structured validation FAIL results
- durable provenance validation
- source-recovery archive coverage validation
- previous-generation compatibility validation
- annotated canonical tag preparation and same-commit failed-attempt recovery
- generated Canonical Gate workflow
- pinned Gitleaks repository-history scan in the generated Canonical Gate
- full local two-checkpoint lifecycle regression
- negative-path tests for schema, malformed containers, coverage, provenance, archive, path boundaries, attestation, and previous-generation constraints
- public CI coverage for the declared Python floor: Python 3.11 and 3.12
- independent disposable Termux validation previously succeeded on Python 3.14.6

## Remaining release proof

The major remaining proof is an external end-to-end run using a fresh GitHub memory repository and a fresh ChatGPT conversation:

1. initialize a new memory repository with `lemp init`;
2. push it to GitHub and allow its Canonical Gate to establish attested CP000001;
3. verify authoritative `lemp sync` and `lemp status` against the exact remote workflow run/attempt;
4. connect that repository to ChatGPT through GitHub with least-privilege permissions;
5. perform `memory sync`;
6. start a fresh conversation and repeat `memory sync`;
7. verify that the synthetic durable decision and state are recovered from the validated canonical snapshot;
8. create a newer unvalidated candidate and verify that it does not contaminate recovered canonical memory.

After that proof, the preview runtime commit pin can be replaced by the first tagged software release.
