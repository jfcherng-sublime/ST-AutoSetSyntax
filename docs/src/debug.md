---
title: Debug
hide:
  - toc
---

--8<-- "refs.md"

## Log Panel

Log messages are printed in the dedicated log panel. There are two ways to open the log panel:

1. Right click on the bottom-left corner of ST and then select `Output: AutoSetSyntax`.
1. Run `AutoSetSyntax: Toggle Log Panel` from the command palette[^1].

To check whether your rules are being dropped during optimization (e.g., due to wrong names
or arguments), (re-)save your plugin/project settings and inspect the log panel for dropped
rules messages.

!!! note

    Each window has its own log panel. They may have different outputs due to project settings.

## Debug Information

Just run `AutoSetSyntax: Debug Information` from the command palette[^1].

!!! tip

    The output is designed to be Python-compatible, thus you can format it
    with a Python formatter like [Ruff][ruff-formatter-online].

## Syntax Rules Summary

Run `AutoSetSyntax: Syntax Rules Summary` from the command palette[^1].

!!! tip

    The output is designed to be Python-compatible, thus you can format it
    with a Python formatter like [Ruff][ruff-formatter-online].

[^1]: Command palette: ++ctrl+p++ for Windows/Linux. ++cmd+p++ for macOS.
