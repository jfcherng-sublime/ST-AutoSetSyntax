---
name: lint-fix
description: Auto-fix ruff lint and format issues across the repo using make ci-fix.
---

Run ruff auto-fix (lint + format):

```bash
cd D:/Repo/ST-AutoSetSyntax && make ci-fix 2>&1
```

After fixing, report what was changed. If there are remaining issues that couldn't be auto-fixed (e.g., mypy errors or unsafe ruff fixes), list them and ask whether to run `make ci-fix-unsafe` for the ruff issues.
