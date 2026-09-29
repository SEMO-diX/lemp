from lemp.path_rules import allowed_memory_path


def test_expected_memory_paths_are_allowed() -> None:
    assert allowed_memory_path("BOOTSTRAP.md")
    assert allowed_memory_path("MANIFEST.yaml")
    assert allowed_memory_path("decisions/D000001.md")
    assert allowed_memory_path("schemas/context-contract.schema.json")
    assert allowed_memory_path(".github/workflows/lemp-canonical.yml")


def test_unmanaged_paths_are_rejected() -> None:
    assert not allowed_memory_path("random.txt")
    assert not allowed_memory_path(".github/workflows/arbitrary.yml")
    assert not allowed_memory_path("../escape.md")
    assert not allowed_memory_path("/absolute/path")
