# Changelog

All notable public changes to LEMP are recorded here.

## v0.1.0 — 2026-10-01

First public MVP release candidate for the LEMP v1.1 reference implementation.

### Included

- GitHub-backed validated canonical snapshots with candidate/canonical separation.
- Synthetic-only `lemp init` repository generation.
- `lemp validate`, `sync`, `status`, `checkpoint`, and `prepare-tag`.
- Context Contract and Applicability schema/routing validation.
- Decision-to-Contract coverage validation.
- Provenance and source-recovery archive validation.
- Annotated Canonical Gate checkpoint attestations from CP000001 for newly generated public repositories.
- Exact remote GitHub Actions run/attempt verification for canonical authority.
- Previous-generation validation as defense in depth against candidate validator weakening.
- Full candidate-delta path/file safety checks and pinned Gitleaks history scanning.
- Structured fail-closed handling for malformed repository inputs.
- Public CI coverage on Python 3.11 and 3.12.
- Fresh-repository / fresh-conversation ChatGPT + GitHub E2E proof, including unvalidated-candidate isolation.

### E2E evidence

The public MVP proof established a fresh synthetic memory repository at remotely attested CP000001, verified authoritative `sync/status`, recovered durable state from fresh ChatGPT conversations, and confirmed that a newer `NEWER_UNVALIDATED` candidate did not contaminate canonical working context.

See `docs/E2E-REPORT.md` for the concrete run IDs, SHAs, and failure/recovery evidence.

### Release compatibility

- Python: 3.11+
- Protocol baseline: LEMP v1.1
- License: Apache-2.0
- Reference integration: ChatGPT + GitHub

### Known boundaries

- LEMP does not sandbox or reduce permissions granted to the GitHub integration.
- Offline attestation is diagnostic-only and is not canonical authority.
- The generated Canonical Gate runtime remains pinned to the exact E2E-tested public commit `738d35931fc6f11fa9eeee68809253233f715fe8`.
- PyPI publishing is not part of the v0.1.0 release gate; GitHub source/tag installation is the initial distribution path.
- Proposed v1.2 Semantic Approval & Authority Separation is not part of v0.1.0.
