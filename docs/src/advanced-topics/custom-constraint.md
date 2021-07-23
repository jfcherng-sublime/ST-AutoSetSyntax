---
hide:
  - toc
---

--8<-- "refs.md"

# Custom `Constraint` Implementation

!!! tip

    You may check how built-in `Constraint`s are implemented [here][plugin-constraints-dir].

You may create your own custom `Constraint` implementation by following steps.

1.  Run `AutoSetSyntax: Create New Constraint` from the command palette[^1].
1.  It will create a template like

    !!! example

        ```py
        --8<-- "../../../templates/example_constraint.py"
        ```

        !!! tip

            There is a `get_view_info` method, which accepts an `sublime.View` as an argument
            and returns a `TD_ViewSnapshot` dict. In the dict, there are some cached information
            about the current view to provide a uniform format and prevent from calling
            resource-consuming function calls several times among rules.

            ```py
            class TD_ViewSnapshot(TypedDict):
                char_count: int
                content: str  # pseudo file content
                file_name: str  # empty string if not on a disk
                file_path: str  # empty string if not on a disk
                file_size: int  # in bytes, -1 if file not on a disk
                first_line: str  # pseudo first line
                syntax: Optional[sublime.Syntax]  # note that the value is as-is when it's cached
            ```

1.  Decide the constraint name of your `Constraint`.

    Say, if your class name is `MyOwnConstraint`, the constraint name is decided by

    1. Remove `Constraint` suffix from the class name. (`MyOwnConstraint` » `MyOwn`)
    1. Convert it into snake case. (`MyOwn` » `my_own`)

    That is, you can use it via `"constraint": "my_own"` in a constraint rule.

1.  At least, implement the `test` method.
1.  Save your implementation in `Packages/AutoSetSyntax-Custom/constraintes/`.
    Conventionally, the file name used is the constraint name, `my_own.py`.

1.  Restart ST and check whether your implementation is loaded via [Debug Information][plugin-debug-information].

[plugin-debug-information]: ../debug.md#debug-information

[^1]: Command palette: ++ctrl+p++ for Windows/Linux. ++cmd+p++ for macOS.
