from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def _safe(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        raise ValueError(f"unsafe repository path: {rel!r}")
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {rel}") from exc
    return target


def _yaml(root: Path, rel: str) -> dict[str, Any]:
    path = _safe(root, rel)
    if not path.is_file():
        raise ValueError(f"missing required file: {rel}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected YAML mapping: {rel}")
    return data


def _json(root: Path, rel: str) -> dict[str, Any]:
    path = _safe(root, rel)
    if not path.is_file():
        raise ValueError(f"missing required file: {rel}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {rel}")
    return data


def _schema_errors(data: dict[str, Any], schema: dict[str, Any], rel: str) -> list[str]:
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(
        validator.iter_errors(data),
        key=lambda item: "/".join(str(x) for x in item.absolute_path),
    ):
        location = ".".join(str(x) for x in error.absolute_path) or "<root>"
        errors.append(f"{rel}: schema violation at {location}: {error.message}")
    return errors


def validate_control_plane(root: Path, manifest: dict[str, Any]) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    control = manifest.get("control_plane")
    if not isinstance(control, dict):
        return ["MANIFEST.control_plane must be a mapping"]
    if control.get("enabled") is not True:
        errors.append("MANIFEST.control_plane.enabled must be true")

    global_path = control.get("global_contract", "contracts/GLOBAL.yaml")
    active_paths = control.get("active_contracts") or []
    if not isinstance(global_path, str):
        errors.append("MANIFEST.control_plane.global_contract must be a path")
        global_path = "contracts/GLOBAL.yaml"
    if not isinstance(active_paths, list) or any(not isinstance(x, str) for x in active_paths):
        errors.append("MANIFEST.control_plane.active_contracts must be a list of paths")
        active_paths = []

    contract_paths: list[str] = []
    for rel in [global_path] + list(active_paths):
        if rel not in contract_paths:
            contract_paths.append(rel)

    try:
        contract_schema = _json(root, "schemas/context-contract.schema.json")
    except Exception as exc:
        errors.append(str(exc))
        contract_schema = {}

    contracts_by_id: dict[str, dict[str, Any]] = {}
    contract_path_by_id: dict[str, str] = {}
    for rel in contract_paths:
        try:
            contract = _yaml(root, rel)
        except Exception as exc:
            errors.append(str(exc))
            continue
        if contract_schema:
            try:
                errors.extend(_schema_errors(contract, contract_schema, rel))
            except Exception as exc:
                errors.append(f"{rel}: invalid contract schema: {exc}")
        cid = contract.get("id")
        if not isinstance(cid, str):
            errors.append(f"{rel}: missing contract id")
            continue
        if cid in contracts_by_id:
            errors.append(f"duplicate contract id: {cid}")
            continue
        if contract.get("protocol") != manifest.get("protocol"):
            errors.append(f"{rel}: protocol does not match MANIFEST")
        if str(contract.get("protocol_version")) != str(manifest.get("protocol_version")):
            errors.append(f"{rel}: protocol_version does not match MANIFEST")
        if contract.get("status") != "active":
            errors.append(f"{rel}: configured contract must be active")
        contracts_by_id[cid] = contract
        contract_path_by_id[cid] = rel

    applicability_path = control.get("applicability_index", "applicability/INDEX.yaml")
    schema_path = control.get("applicability_schema", "schemas/applicability.schema.json")
    if not isinstance(applicability_path, str):
        errors.append("MANIFEST.control_plane.applicability_index must be a path")
        applicability_path = "applicability/INDEX.yaml"
    if not isinstance(schema_path, str):
        errors.append("MANIFEST.control_plane.applicability_schema must be a path")
        schema_path = "schemas/applicability.schema.json"

    try:
        applicability = _yaml(root, applicability_path)
    except Exception as exc:
        errors.append(str(exc))
        return errors

    try:
        applicability_schema = _json(root, schema_path)
        errors.extend(_schema_errors(applicability, applicability_schema, applicability_path))
    except Exception as exc:
        errors.append(f"{applicability_path}: invalid applicability schema: {exc}")

    if applicability.get("protocol") != manifest.get("protocol"):
        errors.append("applicability protocol does not match MANIFEST")
    if str(applicability.get("protocol_version")) != str(manifest.get("protocol_version")):
        errors.append("applicability protocol_version does not match MANIFEST")
    if applicability.get("status") != "active":
        errors.append("applicability index must be active")

    policy = applicability.get("policy") or {}
    expected_policy = {
        "summary_authority": "additive_only",
        "semantic_routing": "additive_only",
        "ambiguity": "union_active_contracts",
        "unresolved_important_memory_routing": "fail_closed",
    }
    if not isinstance(policy, dict):
        errors.append("applicability policy must be a mapping")
        policy = {}
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            errors.append(f"applicability policy.{key} must be {expected!r}")

    binding = policy.get("session_binding") or {}
    minimum_contracts = binding.get("minimum_contracts") or []
    if not isinstance(minimum_contracts, list):
        errors.append("session_binding.minimum_contracts must be a list")
        minimum_contracts = []
    for cid in minimum_contracts:
        if cid not in contracts_by_id:
            errors.append(f"session binding references unknown active contract: {cid}")

    routing = applicability.get("routing") or {}
    routes = routing.get("contracts") or []
    if not isinstance(routes, list):
        errors.append("applicability routing.contracts must be a list")
        routes = []
    route_ids: set[str] = set()
    for route in routes:
        if not isinstance(route, dict):
            errors.append(f"invalid applicability route: {route!r}")
            continue
        cid = route.get("id")
        if cid not in contracts_by_id:
            errors.append(f"applicability route references unknown active contract: {cid!r}")
            continue
        if cid in route_ids:
            errors.append(f"duplicate applicability route for contract: {cid}")
        route_ids.add(cid)

    for cid in contracts_by_id:
        if cid not in route_ids:
            errors.append(f"active contract missing applicability route: {cid}")

    global_id = None
    try:
        global_contract = _yaml(root, global_path)
        if isinstance(global_contract.get("id"), str):
            global_id = global_contract["id"]
    except Exception:
        pass
    if global_id is not None:
        route = next(
            (item for item in routes if isinstance(item, dict) and item.get("id") == global_id),
            None,
        )
        if route is None or route.get("always_on_memory_entry") is not True:
            errors.append("global contract route must be always_on_memory_entry")

    hints = routing.get("semantic_hints") or []
    if not isinstance(hints, list):
        errors.append("applicability routing.semantic_hints must be a list")
        hints = []
    for hint in hints:
        if not isinstance(hint, dict):
            errors.append(f"invalid semantic hint: {hint!r}")
            continue
        cid = hint.get("id")
        if cid not in contracts_by_id:
            errors.append(f"semantic hint references unknown active contract: {cid!r}")
        patterns = hint.get("patterns") or []
        if not isinstance(patterns, list) or any(not isinstance(x, str) for x in patterns):
            errors.append(f"{cid}: semantic hint patterns must be strings")
            continue
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"{cid}: invalid semantic hint regex {pattern!r}: {exc}")

    decision_index_path = control.get("decision_index", "decisions/INDEX.yaml")
    if not isinstance(decision_index_path, str):
        errors.append("MANIFEST.control_plane.decision_index must be a path")
        return errors
    try:
        decision_index = _yaml(root, decision_index_path)
    except Exception as exc:
        errors.append(str(exc))
        return errors

    decisions = decision_index.get("decisions") or []
    if not isinstance(decisions, list):
        errors.append("decision index decisions must be a list")
        return errors

    decision_by_path: dict[str, dict[str, Any]] = {}
    for entry in decisions:
        if not isinstance(entry, dict):
            errors.append(f"invalid decision index entry: {entry!r}")
            continue
        did = entry.get("id")
        rel = entry.get("path")
        if not isinstance(did, str) or re.fullmatch(r"D\d{6}", did) is None:
            errors.append(f"invalid decision id: {did!r}")
            continue
        if not isinstance(rel, str):
            errors.append(f"{did}: invalid decision path")
            continue
        decision_by_path[rel] = entry
        if entry.get("status") != "active":
            continue

        impact = entry.get("context_impact")
        if not isinstance(impact, dict):
            errors.append(f"{did}: active decision missing context_impact")
            continue
        mode = impact.get("mode")
        if mode == "none":
            reason = impact.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"{did}: context_impact none requires reason")
            continue
        if mode != "required":
            errors.append(f"{did}: context_impact.mode must be required or none")
            continue

        contract_ids = impact.get("contracts")
        if not isinstance(contract_ids, list) or not contract_ids:
            errors.append(f"{did}: required context impact must name contracts")
            continue
        for cid in contract_ids:
            contract = contracts_by_id.get(cid)
            if contract is None:
                errors.append(f"{did}: context impact references unknown contract {cid}")
                continue
            if rel not in (contract.get("required") or []):
                errors.append(f"contract coverage mismatch: {cid} is missing {rel}")

    for cid, contract in contracts_by_id.items():
        for rel in contract.get("required") or []:
            if not isinstance(rel, str) or not rel.startswith("decisions/"):
                continue
            entry = decision_by_path.get(rel)
            if entry is None:
                errors.append(f"{cid}: required decision path is not indexed: {rel}")
                continue
            if entry.get("status") != "active":
                errors.append(f"{cid}: required decision is not active: {rel}")
                continue
            impact = entry.get("context_impact") or {}
            if impact.get("mode") != "required" or cid not in (impact.get("contracts") or []):
                errors.append(
                    f"reverse contract coverage mismatch: {cid} requires {rel} "
                    "but decision does not declare that contract"
                )

    return errors
