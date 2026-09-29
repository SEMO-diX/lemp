# Security

## Trust boundary

LEMP validates memory structure and canonical authority. It does **not** sandbox the permissions granted to the GitHub integration, a GitHub token, GitHub Actions, or another agent.

A connector with write access can change candidate repository state. A connector with broad repository permissions may be able to affect more than memory content. Treat connector permissions as part of the deployment trust boundary.

## Recommended permission posture

Use a dedicated private repository for real memory where practical. Prefer read access for synchronization and retrieval. Grant write capability only when write-back or checkpoint preparation is required. Unrestricted GitHub actions are not required for read-oriented synchronization.

The exact controls exposed by ChatGPT/GitHub can change over time, so users should verify the current product permission screen rather than treating screenshots or this document as an immutable permissions specification.

## Secrets

Do not store credentials, private keys, tokens, passwords, or other authentication secrets in a LEMP memory repository.

## Public repository rule

This public repository must contain only synthetic examples and public implementation material. Do not copy real private memory records here.

## Reporting

Until a dedicated security reporting channel is published, avoid placing sensitive vulnerability details in public issues.
