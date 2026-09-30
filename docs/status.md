# Implementation status

Updated: 2026-10-01

## Release-hardening state

The public implementation has completed the fresh-repository / fresh-conversation MVP proof. Public CI covers Python 3.11 and 3.12, and both versions are required to remain green for release changes.

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

## External E2E proof

The external fresh-repository / fresh-conversation proof is complete.

Verified outcomes include:

- attested CP000001 promotion in a fresh private GitHub memory repository;
- exact remote workflow run/attempt verification;
- authoritative `lemp sync` and `lemp status` with `PASS`;
- fresh ChatGPT recovery of synthetic durable state and latest decision without expected answers in the prompt;
- detection of a newer unvalidated `main` as `NEWER_UNVALIDATED`;
- candidate-only content excluded from canonical working context;
- failed Canonical Gate promotion when the unvalidated candidate did not advance the checkpoint correctly.

See [E2E-REPORT.md](E2E-REPORT.md) for concrete evidence.

The next release step is the first tagged software release.
