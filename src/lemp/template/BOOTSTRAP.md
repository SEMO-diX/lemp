# LEMP Bootstrap

Synthetic LEMP v1.1 template.

Synchronization semantics:

- canonical authority is the newest valid `lemp-valid/CPxxxxxx` checkpoint, not an unvalidated branch head;
- one exact commit SHA is pinned for a synchronization pass;
- `MANIFEST.yaml`, `STATE.md`, declared required context, active Context Contracts, and required critical invariants come from that same snapshot;
- checkpoint and state-version mismatches, missing required context, missing critical invariants, or unresolved critical conflicts produce `FAIL`;
- optional-context absence may produce `PARTIAL`; otherwise the result is `PASS`;
- durable context is used only after the integrity result is established.

For CP000017 and later, production conformance also includes annotated canonical attestation and authoritative workflow-run verification. The public preview CLI currently validates the local tag object only.
