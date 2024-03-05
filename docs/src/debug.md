---
title: Debug
hide:
  - toc
---

--8<-- "refs.md"

## Log Panel

Log messages are printed in the dedicated log panel. There are two ways to open the log panel:

1. Right click on the bottom-left corner of ST and then select `Output: AutoSetSyntax`.
   Or, run `AutoSetSyntax: Show Log Panel` from the command palette[^1].
1. (Re-)save your plugin/project settings.
1. See whether your rules are in those dropped rules.
   In that case, it's likely that your rules have wrong name or args.

!!! note

    Each window has its own log panel. They may have different outputs due to project settings.

## Debug Information

1. Run `AutoSetSyntax: Debug Information` from the command palette[^1].
1. The debug information will be copied to the clipboard.

!!! tip

    The debug information is designed to be Python-compatible, thus you can format it
    with a Python formatter like [Ruff][ruff-formatter-online].

[^1]: Command palette: ++ctrl+p++ for Windows/Linux. ++cmd+p++ for macOS.
