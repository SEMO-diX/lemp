"""Synthetic memory template used by `lemp init`.

All content in this module is fabricated for the public demonstration.
No private memory records are copied here.
"""

TEMPLATE_FILES: dict[str, str] = {
    "README.md": """# Synthetic LEMP memory

This repository contains fabricated demo memory for exercising LEMP.
""",
    "BOOTSTRAP.md": """# LEMP Bootstrap

Synthetic LEMP v1.1 template.

Synchronization semantics:

- canonical authority is the newest valid `lemp-valid/CPxxxxxx` checkpoint, not an unvalidated branch head;
- one exact commit SHA is pinned for a synchronization pass;
- `MANIFEST.yaml`, `STATE.md`, declared required context, active Context Contracts, and required critical invariants come from that same snapshot;
- checkpoint and state-version mismatches, missing required context, missing critical invariants, or unresolved critical conflicts produce `FAIL`;
- optional-context absence may produce `PARTIAL`; otherwise the result is `PASS`;
- durable context is used only after the integrity result is established.

For CP000017 and later, production conformance also includes annotated canonical attestation and authoritative workflow-run verification. The public preview CLI currently validates the local tag object only.
""",
    "MANIFEST.yaml": """protocol: LEMP
protocol_version: "1.1"
status: Draft
memory_version: 1
checkpoint: CP000001
latest_session: S000001
latest_event: E000001
latest_decision: D000001
state_version: 1
updated_at: "2026-09-29"

required_context:
  - BOOTSTRAP.md
  - STATE.md
  - contracts/GLOBAL.yaml
  - contracts/demo.yaml
  - invariants/INDEX.yaml
  - decisions/INDEX.yaml
  - conflicts/INDEX.yaml
  - archive/INDEX.yaml
  - state/CURRENT.yaml
  - applicability/INDEX.yaml
  - topics/demo.md

critical_memories:
  - decisions/D000001.md

active_topics:
  - topics/demo.md

control_plane:
  enabled: true
  global_contract: contracts/GLOBAL.yaml
  active_contracts:
    - contracts/demo.yaml
  invariant_index: invariants/INDEX.yaml
  decision_index: decisions/INDEX.yaml
  conflict_index: conflicts/INDEX.yaml
  current_state: state/CURRENT.yaml
  applicability_index: applicability/INDEX.yaml
  applicability_schema: schemas/applicability.schema.json
  integrity_gate:
    statuses: [PASS, PARTIAL, FAIL]
    fail_closed_on:
      - checkpoint_mismatch
      - state_version_mismatch
      - missing_required_context
      - missing_critical_invariant
      - unresolved_critical_conflict
      - current_state_mismatch
      - applicability_unresolved
      - contract_coverage_mismatch

canonical:
  candidate_ref: main
  validated_tag_prefix: "lemp-valid/"
  require_validated_snapshot: true
  pin_snapshot_sha: true
  fallback_to_last_validated: true
  promotion_workflow: .github/workflows/lemp-canonical.yml
  attestation_required_from: CP000017
  attestation_version: 1
  attestation_workflow: .github/workflows/lemp-canonical.yml
  remote_workflow_verification_required: true
  offline_attestation_authoritative: false
  refresh_remote_tags_before_resolution: true
  prune_stale_remote_tags: true
  verify_exact_attested_run_attempt: true
  recover_failed_attestation_same_commit_only: true
  recover_failed_attestation_force_with_lease: true

archive_policy:
  recursive_summary_only: false
  source_recovery_required: true
  immutable_preferred: true
  checkpointed_session_archive_required: true
  index: archive/INDEX.yaml

security:
  secrets_allowed: false
""",
    "STATE.md": """# Current State

State-Version: 1
Updated: 2026-09-29
Checkpoint: CP000001

## Current truths

- This repository is synthetic demonstration memory.
- GitHub is the durable external memory store.
- Conversation context is temporary and non-canonical.
- The selected canonical checkpoint must be validated before durable context is trusted.
- The demo application backend is FastAPI.
- The demo database is PostgreSQL.
- Offline mode is not part of the demo MVP.

## Integrity notes

- MANIFEST checkpoint expected: `CP000001`
- MANIFEST state version expected: `1`
- This file Checkpoint: `CP000001`
- This file State-Version: `1`
""",
    "contracts/GLOBAL.yaml": """id: CTX-GLOBAL
protocol: LEMP
protocol_version: "1.1"
version: 1
status: active
scope:
  - "*"
required:
  - MANIFEST.yaml
  - STATE.md
  - invariants/INDEX.yaml
  - conflicts/INDEX.yaml
  - archive/INDEX.yaml
  - state/CURRENT.yaml
  - applicability/INDEX.yaml
required_invariants:
  - INV000001
  - INV000002
  - INV000003
optional: []
checks:
  repository_available: true
  checkpoint_match: true
  state_version_match: true
  required_context_exists: true
  critical_invariants_active: true
  unresolved_critical_conflicts: false
integrity_gate:
  fail_closed: true
  fail_on:
    - checkpoint_mismatch
    - state_version_mismatch
    - missing_required_context
    - missing_critical_invariant
    - unresolved_critical_conflict
    - current_state_mismatch
    - applicability_unresolved
    - contract_coverage_mismatch
archive_policy:
  on_conflict: true
  on_uncertainty: true
  otherwise: false
""",
    "contracts/demo.yaml": """id: CTX-DEMO
protocol: LEMP
protocol_version: "1.1"
version: 1
status: active
topic: demo
required:
  - state/CURRENT.yaml
  - decisions/D000001.md
  - topics/demo.md
required_invariants:
  - INV000001
  - INV000002
  - INV000003
optional:
  - reports/latest.md
archive_policy:
  on_conflict: true
  on_uncertainty: true
  on_source_verification: true
  otherwise: false
reasoning_policy:
  require_integrity_gate_for_important_tasks: true
  allow_partial_for_noncritical_tasks: true
""",
    "invariants/INDEX.yaml": """protocol: LEMP
protocol_version: "1.1"
invariants:
  - id: INV000001
    path: invariants/INV000001.yaml
    status: active
    severity: critical
  - id: INV000002
    path: invariants/INV000002.yaml
    status: active
    severity: critical
  - id: INV000003
    path: invariants/INV000003.yaml
    status: active
    severity: critical
""",
    "invariants/INV000001.yaml": """id: INV000001
status: active
severity: critical
statement: Canonical persistent memory comes from the validated GitHub repository snapshot, not from conversational recollection.
source:
  decision: D000001
  path: decisions/D000001.md
""",
    "invariants/INV000002.yaml": """id: INV000002
status: active
severity: critical
statement: Authentication secrets must never be stored in this memory repository.
source:
  decision: D000001
  path: decisions/D000001.md
""",
    "invariants/INV000003.yaml": """id: INV000003
status: active
severity: critical
statement: Important memory-dependent reasoning requires integrity verification and fails closed when required context is missing.
source:
  decision: D000001
  path: decisions/D000001.md
""",
    "decisions/INDEX.yaml": """protocol: LEMP
protocol_version: "1.1"
decisions:
  - id: D000001
    path: decisions/D000001.md
    status: active
    supersedes: null
    superseded_by: null
    extends: []
    context_impact:
      mode: required
      contracts:
        - CTX-DEMO
""",
    "decisions/D000001.md": """---
id: D000001
status: active
source_session: S000001
source_event: E000001
---

# Demo MVP architecture

The synthetic project uses FastAPI for the backend and PostgreSQL for storage. Offline mode is explicitly outside the synthetic MVP.

This record exists only to demonstrate durable cross-session decision recovery.
""",
    "conflicts/INDEX.yaml": """protocol: LEMP
protocol_version: "1.1"
conflicts: []
""",
    "state/CURRENT.yaml": """protocol: LEMP
protocol_version: "1.1"
version: 1
checkpoint: CP000001
status: active
facts:
  backend:
    value: FastAPI
    source_decisions: [D000001]
  database:
    value: PostgreSQL
    source_decisions: [D000001]
  offline_mode:
    value: excluded_from_mvp
    source_decisions: [D000001]
""",
    "applicability/INDEX.yaml": """protocol: LEMP
protocol_version: "1.1"
version: 1
status: active
policy:
  summary_authority: additive_only
  semantic_routing: additive_only
  ambiguity: union_active_contracts
  unresolved_important_memory_routing: fail_closed
  session_binding:
    enabled: true
    minimum_contracts:
      - CTX-GLOBAL
routing:
  memory_entry:
    command_prefixes:
      - memory
    literals:
      - memory sync
      - memory status
      - memory checkpoint
    resource_literals:
      - MANIFEST.yaml
      - STATE.md
  contracts:
    - id: CTX-GLOBAL
      always_on_memory_entry: true
      command_prefixes: []
      topic_literals: []
      resource_literals: []
    - id: CTX-DEMO
      always_on_memory_entry: false
      command_prefixes:
        - demo
      topic_literals:
        - demo
      resource_literals:
        - decisions/D000001.md
        - topics/demo.md
  semantic_hints:
    - id: CTX-DEMO
      patterns:
        - "(?i)backend|database|offline|demo"
""",
    "archive/INDEX.yaml": """protocol: LEMP
protocol_version: "1.1"
version: 1
policy:
  checkpointed_session_archive_required: true
  allowed_record_types:
    - source-recovery
  expected_status: immutable-preferred
records:
  - session: S000001
    path: archive/S000001-source.md
    record_type: source-recovery
    status: immutable-preferred
""",
    "archive/S000001-source.md": """# Source Recovery — S000001

Synthetic source material for the public LEMP demonstration.

The demo chose FastAPI, PostgreSQL, and excluded offline mode from MVP scope. No real user memory is contained in this archive.
""",
    "sessions/S000001.md": """---
id: S000001
date: 2026-09-29
previous: null
checkpoint_after: CP000001
state_version_after: 1
---

# Session S000001

Initialized the synthetic demonstration memory and recorded its first durable architecture decision.
""",
    "events/E000001.md": """---
id: E000001
type: synthetic_demo_initialized
source_session: S000001
supersedes: null
status: active
created_by: example
confidence: explicit
---

# Synthetic demo initialized

The public demonstration memory was initialized with fully synthetic project facts.
""",
    "topics/demo.md": """---
id: demo
checkpoint: CP000001
status: active
---

# Synthetic Demo Project

Current durable architecture:

- backend: FastAPI
- database: PostgreSQL
- offline mode: excluded from MVP

The point of this topic is to make fresh-conversation recovery visible and easy to test.
""",
    "reports/latest.md": """# Synthetic status report

The fabricated demo is at MVP planning stage. No real project or personal information is present.
""",
    "schemas/applicability.schema.json": """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.invalid/lemp/schemas/applicability.schema.json",
  "title": "LEMP v1.1 Applicability Index",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "protocol",
    "protocol_version",
    "version",
    "status",
    "policy",
    "routing"
  ],
  "properties": {
    "protocol": {
      "type": "string",
      "minLength": 1
    },
    "protocol_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+$"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "status": {
      "enum": [
        "active",
        "inactive",
        "deprecated"
      ]
    },
    "policy": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "summary_authority",
        "semantic_routing",
        "ambiguity",
        "unresolved_important_memory_routing",
        "session_binding"
      ],
      "properties": {
        "summary_authority": {
          "const": "additive_only"
        },
        "semantic_routing": {
          "const": "additive_only"
        },
        "ambiguity": {
          "const": "union_active_contracts"
        },
        "unresolved_important_memory_routing": {
          "const": "fail_closed"
        },
        "session_binding": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "enabled",
            "minimum_contracts"
          ],
          "properties": {
            "enabled": {
              "const": true
            },
            "minimum_contracts": {
              "type": "array",
              "minItems": 1,
              "uniqueItems": true,
              "items": {
                "type": "string",
                "pattern": "^CTX-[A-Z0-9][A-Z0-9-]*$"
              }
            }
          }
        }
      }
    },
    "routing": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "memory_entry",
        "contracts",
        "semantic_hints"
      ],
      "properties": {
        "memory_entry": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "command_prefixes",
            "literals",
            "resource_literals"
          ],
          "properties": {
            "command_prefixes": {
              "type": "array",
              "uniqueItems": true,
              "items": {
                "type": "string",
                "minLength": 1
              }
            },
            "literals": {
              "type": "array",
              "uniqueItems": true,
              "items": {
                "type": "string",
                "minLength": 1
              }
            },
            "resource_literals": {
              "type": "array",
              "uniqueItems": true,
              "items": {
                "type": "string",
                "minLength": 1
              }
            }
          }
        },
        "contracts": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "id",
              "always_on_memory_entry",
              "command_prefixes",
              "topic_literals",
              "resource_literals"
            ],
            "properties": {
              "id": {
                "type": "string",
                "pattern": "^CTX-[A-Z0-9][A-Z0-9-]*$"
              },
              "always_on_memory_entry": {
                "type": "boolean"
              },
              "command_prefixes": {
                "type": "array",
                "uniqueItems": true,
                "items": {
                  "type": "string",
                  "minLength": 1
                }
              },
              "topic_literals": {
                "type": "array",
                "uniqueItems": true,
                "items": {
                  "type": "string",
                  "minLength": 1
                }
              },
              "resource_literals": {
                "type": "array",
                "uniqueItems": true,
                "items": {
                  "type": "string",
                  "minLength": 1
                }
              }
            }
          }
        },
        "semantic_hints": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "id",
              "patterns"
            ],
            "properties": {
              "id": {
                "type": "string",
                "pattern": "^CTX-[A-Z0-9][A-Z0-9-]*$"
              },
              "patterns": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": true,
                "items": {
                  "type": "string",
                  "minLength": 1
                }
              }
            }
          }
        }
      }
    }
  }
}
""",
    "schemas/context-contract.schema.json": """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.invalid/lemp/schemas/context-contract.schema.json",
  "title": "LEMP v1.1 Context Contract",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "protocol",
    "protocol_version",
    "version",
    "status",
    "required",
    "required_invariants",
    "archive_policy"
  ],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^CTX-[A-Z0-9][A-Z0-9-]*$"
    },
    "protocol": {
      "type": "string",
      "minLength": 1
    },
    "protocol_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+$"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "status": {
      "enum": [
        "active",
        "inactive",
        "deprecated"
      ]
    },
    "scope": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "topic": {
      "type": "string",
      "minLength": 1
    },
    "required": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "required_invariants": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "pattern": "^INV[0-9]{6}$"
      }
    },
    "optional": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "checks": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "repository_available",
        "checkpoint_match",
        "state_version_match",
        "required_context_exists",
        "critical_invariants_active",
        "unresolved_critical_conflicts"
      ],
      "properties": {
        "repository_available": {
          "type": "boolean"
        },
        "checkpoint_match": {
          "type": "boolean"
        },
        "state_version_match": {
          "type": "boolean"
        },
        "required_context_exists": {
          "type": "boolean"
        },
        "critical_invariants_active": {
          "type": "boolean"
        },
        "unresolved_critical_conflicts": {
          "type": "boolean"
        }
      }
    },
    "integrity_gate": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "fail_closed",
        "fail_on"
      ],
      "properties": {
        "fail_closed": {
          "type": "boolean"
        },
        "fail_on": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {
            "type": "string",
            "minLength": 1
          }
        }
      }
    },
    "archive_policy": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "on_conflict",
        "on_uncertainty",
        "otherwise"
      ],
      "properties": {
        "on_conflict": {
          "type": "boolean"
        },
        "on_uncertainty": {
          "type": "boolean"
        },
        "on_source_verification": {
          "type": "boolean"
        },
        "otherwise": {
          "type": "boolean"
        }
      }
    },
    "reasoning_policy": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "require_integrity_gate_for_important_tasks",
        "allow_partial_for_noncritical_tasks"
      ],
      "properties": {
        "require_integrity_gate_for_important_tasks": {
          "type": "boolean"
        },
        "allow_partial_for_noncritical_tasks": {
          "type": "boolean"
        }
      }
    }
  },
  "oneOf": [
    {
      "required": [
        "scope"
      ],
      "not": {
        "required": [
          "topic"
        ]
      }
    },
    {
      "required": [
        "topic"
      ],
      "not": {
        "required": [
          "scope"
        ]
      }
    }
  ]
}
""",
    ".github/workflows/lemp-canonical.yml": """name: LEMP Canonical Gate

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

concurrency:
  group: lemp-canonical-promotion
  cancel-in-progress: false

env:
  LEMP_RUNTIME_SPEC: git+https://github.com/SEMO-diX/lemp.git@main

jobs:
  gate:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
    steps:
      - name: Check out complete memory history
        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          fetch-depth: 0
          fetch-tags: true

      - name: Set up Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: "3.12"

      - name: Install LEMP reference runtime
        run: python -m pip install --disable-pip-version-check "$LEMP_RUNTIME_SPEC"

      - name: Validate memory structure
        run: lemp validate --root . --format json

      - name: Scan repository history for secrets
        shell: bash
        run: |
          set -euo pipefail
          docker run --rm \
            --user "$(id -u):$(id -g)" \
            -v "$PWD:/repo:ro" \
            -w /repo \
            ghcr.io/gitleaks/gitleaks:v8.29.1@sha256:aa036a2f4bdfe3cc3c55fa4326308efabb4a6be498c883c864fd1d0d5585438a \
            git --redact --no-banner /repo

      - name: Validate checkpoint sequence
        if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
        env:
          GH_TOKEN: ${{ github.token }}
        shell: bash
        run: |
          set -euo pipefail
          if git tag --list 'lemp-valid/CP*' | grep -q .; then
            lemp checkpoint --root . --allow-main --check-only --format json
          else
            python - <<'PY'
          import yaml
          manifest = yaml.safe_load(open("MANIFEST.yaml", encoding="utf-8")) or {}
          if manifest.get("checkpoint") != "CP000001":
              raise SystemExit("first canonical checkpoint must be CP000001")
          print("PASS: bootstrap checkpoint CP000001")
          PY

  promote:
    needs: gate
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: write
    steps:
      - name: Check out validated commit with tags
        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          fetch-depth: 0
          fetch-tags: true

      - name: Set up Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: "3.12"

      - name: Install LEMP reference runtime
        run: python -m pip install --disable-pip-version-check "$LEMP_RUNTIME_SPEC"

      - name: Prepare and push exact canonical tag
        env:
          GH_TOKEN: ${{ github.token }}
        shell: bash
        run: |
          set -euo pipefail
          git fetch --force --prune --prune-tags --tags origin
          result="$(lemp prepare-tag --root . --format json)"
          echo "$result"
          action="$(python -c 'import json,sys; print(json.load(sys.stdin)["action"])' <<<"$result")"
          tag="$(python -c 'import json,sys; print(json.load(sys.stdin)["tag"])' <<<"$result")"
          expected_ref="$(python -c 'import json,sys; print(json.load(sys.stdin).get("expected_remote_ref") or "")' <<<"$result")"
          case "$action" in
            CREATE)
              git push origin "refs/tags/$tag"
              ;;
            KEEP_VALID)
              echo "$tag already has a successful attestation."
              ;;
            RECOVER_FAILED)
              test -n "$expected_ref"
              git push --force-with-lease="refs/tags/$tag:$expected_ref" origin "refs/tags/$tag"
              ;;
            *)
              echo "Unknown promotion action: $action"
              exit 1
              ;;
          esac

      - name: Smoke-test promoted snapshot locally
        run: lemp sync --root . --offline-attestation --format json
""",
}
