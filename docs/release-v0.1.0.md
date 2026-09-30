# LEMP v0.1.0 Release

Date: 2026-10-01

## Release intent

v0.1.0 freezes the public LEMP v1.1 MVP reference implementation that has already completed a fresh-repository / fresh-conversation external proof.

This release is intentionally a packaging and release-boundary milestone rather than a protocol or runtime-semantics expansion.

## Release commit requirements

The release tag must point to the exact `main` commit that passes the v0.1.0 release gate.

The `v0.1.0` tag must not be moved after publication. If a defect is found after release, publish a later patch release instead of replacing the existing tag.

## Required release gate

The release commit must satisfy all of the following:

1. Public LEMP CI succeeds on Python 3.11 and 3.12.
2. The full pytest suite succeeds.
3. `python -m build` creates both wheel and sdist.
4. A fresh virtual environment installs the built wheel successfully.
5. Installed package metadata reports version `0.1.0`.
6. Installed `lemp --help` succeeds.
7. Installed `lemp init` generates a synthetic CP000001 repository.
8. Installed `lemp validate` returns `PASS` for that generated repository.
9. The generated default runtime source remains the immutable E2E-tested commit:
   `git+https://github.com/SEMO-diX/lemp.git@738d35931fc6f11fa9eeee68809253233f715fe8`.
10. README, changelog, implementation status, and this release note agree on release scope and limitations.

## Distribution

The initial supported distribution path is installation from the GitHub source tag, for example:

```bash
python -m pip install "git+https://github.com/SEMO-diX/lemp.git@v0.1.0"
```

PyPI publication is intentionally not a prerequisite for v0.1.0. A later release-engineering change may add trusted publishing after the GitHub-tagged release path is proven.

## Runtime pin policy

The generated memory workflow does **not** switch its default runtime dependency to `@v0.1.0` in this release.

It stays pinned to the exact E2E-tested commit:

```text
738d35931fc6f11fa9eeee68809253233f715fe8
```

This preserves the exact implementation that passed the external fresh-repository proof. The human-facing software release tag and the generated workflow runtime authority therefore remain intentionally separate in v0.1.0.

A future release may reconsider this once release-artifact provenance and tag-based runtime reproducibility are separately demonstrated.

## External proof carried into this release

The MVP E2E demonstrated:

- fresh private synthetic GitHub memory repository initialization;
- remotely attested CP000001 promotion;
- exact workflow-run/attempt canonical verification;
- authoritative `lemp sync` and `lemp status` PASS;
- fresh ChatGPT recovery without expected durable answers supplied in the prompt;
- detection of a newer unvalidated main candidate;
- exclusion of candidate-only content from canonical working context.

The same E2E exposed a generated CP000001 Canonical Gate shell defect. The defect was repaired before this release and protected by a generated-shell syntax regression.

See `E2E-REPORT.md` for exact evidence.

## Security and trust boundary

LEMP verifies repository-declared memory integrity and canonical authority. It does not create a permission sandbox around GitHub itself.

Users should prefer dedicated memory repositories and least-privilege GitHub access. Authentication secrets must never be stored in a LEMP memory repository.

## Post-release verification

After the `v0.1.0` tag exists, verify installation from the tag in a fresh environment:

```bash
python -m venv /tmp/lemp-v0.1.0
/tmp/lemp-v0.1.0/bin/python -m pip install \
  "git+https://github.com/SEMO-diX/lemp.git@v0.1.0"
/tmp/lemp-v0.1.0/bin/lemp --help
/tmp/lemp-v0.1.0/bin/lemp init /tmp/lemp-v0.1.0-demo
/tmp/lemp-v0.1.0/bin/lemp validate \
  --root /tmp/lemp-v0.1.0-demo \
  --format json
```

Expected integrity result: `PASS`.
