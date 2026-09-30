from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lemp.runtime import init_memory, validate


def memory(tmp_path: Path) -> Path:
    root = tmp_path / "memory"
    init_memory(root)
    return root


def test_contract_schema_violation_fails(tmp_path: Path) -> None:
    root = memory(tmp_path)
    contract = root / "contracts" / "demo.yaml"
    data = yaml.safe_load(contract.read_text(encoding="utf-8"))
    data.pop("archive_policy")
    contract.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("schema violation" in error for error in result.errors)


def test_decision_contract_coverage_mismatch_fails(tmp_path: Path) -> None:
    root = memory(tmp_path)
    contract = root / "contracts" / "demo.yaml"
    data = yaml.safe_load(contract.read_text(encoding="utf-8"))
    data["required"].remove("decisions/D000001.md")
    contract.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("coverage mismatch" in error for error in result.errors)


def test_broken_provenance_fails(tmp_path: Path) -> None:
    root = memory(tmp_path)
    decision = root / "decisions" / "D000001.md"
    decision.write_text(
        decision.read_text(encoding="utf-8").replace(
            "source_session: S000001",
            "source_session: S999999",
        ),
        encoding="utf-8",
    )

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("unknown session" in error for error in result.errors)


def test_missing_archive_coverage_fails(tmp_path: Path) -> None:
    root = memory(tmp_path)
    index = root / "archive" / "INDEX.yaml"
    data = yaml.safe_load(index.read_text(encoding="utf-8"))
    data["records"] = []
    index.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("archive" in error.lower() for error in result.errors)


def test_malformed_manifest_yaml_returns_fail(tmp_path: Path) -> None:
    root = memory(tmp_path)
    (root / "MANIFEST.yaml").write_text("control_plane: [\n", encoding="utf-8")

    result = validate(root)
    assert result.integrity == "FAIL"
    assert result.errors
    assert any("cannot read YAML" in error for error in result.errors)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("critical_memories", "decisions/D000001.md", "MANIFEST.critical_memories must be a list"),
        ("required_context", {"STATE.md": True}, "MANIFEST.required_context must be a list"),
        ("archive_policy", ["archive/INDEX.yaml"], "MANIFEST.archive_policy must be a mapping"),
    ],
)
def test_malformed_manifest_container_types_return_fail(
    tmp_path: Path,
    field: str,
    value: object,
    expected: str,
) -> None:
    root = memory(tmp_path)
    manifest_path = root / "MANIFEST.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = value
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    result = validate(root)
    assert result.integrity == "FAIL"
    assert expected in result.errors


def test_malformed_active_contracts_returns_fail(tmp_path: Path) -> None:
    root = memory(tmp_path)
    manifest_path = root / "MANIFEST.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["control_plane"]["active_contracts"] = "contracts/demo.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("active_contracts must be a list" in error for error in result.errors)


def test_malformed_contract_required_returns_fail(tmp_path: Path) -> None:
    root = memory(tmp_path)
    contract_path = root / "contracts" / "demo.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["required"] = {"decisions/D000001.md": True}
    contract_path.write_text(
        yaml.safe_dump(contract, sort_keys=False),
        encoding="utf-8",
    )

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("contracts/demo.yaml.required must be a list" in error for error in result.errors)


def test_malformed_applicability_mapping_returns_fail_without_exception(
    tmp_path: Path,
) -> None:
    root = memory(tmp_path)
    applicability_path = root / "applicability" / "INDEX.yaml"
    applicability = yaml.safe_load(applicability_path.read_text(encoding="utf-8"))
    applicability["routing"] = ["not", "a", "mapping"]
    applicability_path.write_text(
        yaml.safe_dump(applicability, sort_keys=False),
        encoding="utf-8",
    )

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("applicability routing must be a mapping" in error for error in result.errors)


def test_malformed_invariant_index_returns_fail(tmp_path: Path) -> None:
    root = memory(tmp_path)
    index_path = root / "invariants" / "INDEX.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    index["invariants"] = {"INV000001": "invariants/INV000001.yaml"}
    index_path.write_text(
        yaml.safe_dump(index, sort_keys=False),
        encoding="utf-8",
    )

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("invariants must be a list" in error for error in result.errors)


def test_malformed_archive_records_returns_fail(tmp_path: Path) -> None:
    root = memory(tmp_path)
    index_path = root / "archive" / "INDEX.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    index["records"] = "archive/S000001-source.md"
    index_path.write_text(
        yaml.safe_dump(index, sort_keys=False),
        encoding="utf-8",
    )

    result = validate(root)
    assert result.integrity == "FAIL"
    assert any("archive index records must be a list" in error for error in result.errors)
