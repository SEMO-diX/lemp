# Architecture

```text
ChatGPT
   |
   | GitHub integration (transport / memory I/O)
   v
GitHub memory repository
   |
   | candidate branch: mutable working state
   | validated tag: canonical checkpoint
   v
LEMP control plane
   |
   +-- MANIFEST
   +-- STATE
   +-- Context Contracts
   +-- Critical Invariants
   +-- Applicability
   +-- Decisions / provenance
   +-- source-recovery archive
   v
PASS / PARTIAL / FAIL
```

The key separation is that the newest repository state is not automatically canonical memory. Synchronization selects a validated checkpoint, pins one commit SHA, and reads required context from that one snapshot.

The reference runtime resolves canonical tags and validates a pinned snapshot. For CP000017 and later, it requires an annotated Canonical Gate attestation and verifies the exact GitHub Actions run/attempt by default. An explicit `--offline-attestation` mode exists only for local diagnostics.

The ChatGPT integration is deliberately an integration layer rather than the definition of LEMP itself. Other agents can implement the same protocol against Git or GitHub later.
