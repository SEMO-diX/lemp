# Contributing

LEMP is in public MVP development.

Contributions should keep three boundaries explicit:

1. public implementation must not depend on private memory history;
2. synthetic examples must remain fully fabricated;
3. changes that weaken canonical validation or permission guidance must be called out explicitly.

Before proposing a change, run:

```bash
python -m pip install -e ".[test]"
pytest -q
```

Contributions are made under the repository's Apache License 2.0 terms.
