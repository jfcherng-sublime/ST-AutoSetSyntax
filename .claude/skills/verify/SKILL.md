---
name: verify
description: Run the full CI gate for this repo (mypy + ruff lint + ruff format check + pytest). Use before committing or marking work complete.
---

Run the full CI check suite:

```bash
cd D:/Repo/ST-AutoSetSyntax && make ci-check 2>&1
cd D:/Repo/ST-AutoSetSyntax && make test 2>&1
```

Report any failures clearly. If ruff or mypy errors are found, show the specific lines and suggest fixes. If tests fail, show the failing test output.
