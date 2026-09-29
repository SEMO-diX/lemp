from __future__ import annotations

from pathlib import Path

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
