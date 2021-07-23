---
hide:
  - toc
---

--8<-- "refs.md"

# Custom `Match` Implementation

!!! tip

    You may check how built-in `Match`es are implemented [here][plugin-matches-dir].

You may create your own custom `Match` implementation by following steps.

1.  Run `AutoSetSyntax: Create New Match` from the command palette[^1].
1.  It will create a template like

    !!! example

        ```py
        --8<-- "../../../templates/example_match.py"
        ```

1.  Decide the match name of your `Match`.

    Say, if your class name is `MyOwnMatch`, the match name is decided by

    1. Remove `Match` suffix from the class name. (`MyOwnMatch` » `MyOwn`)
    1. Convert it into snake case. (`MyOwn` » `my_own`)

    That is, you can use it via `"match": "my_own"` in a match rule.

1.  At least, implement the `test` method.
1.  Save your implementation in `Packages/AutoSetSyntax-Custom/matches/`.
    Conventionally, the file name used is the match name, `my_own.py`.

1.  Restart ST and check whether your implementation is loaded via [Debug Information][plugin-debug-information].

[plugin-debug-information]: ../debug.md#debug-information

[^1]: Command palette: ++ctrl+p++ for Windows/Linux. ++cmd+p++ for macOS.
