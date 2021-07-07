---
hide:
  - toc
---

--8<-- "refs.md"

# Migration

!!! tip

    Feel free to [file an issue][autosetsyntax-new-issue] if you have a problem during migration.

## From AutoSetSyntax v1

Please follow steps below.

1. Go `Preferences` => `Package Settings` => `AutoSetSyntax` => `Settings`.
1. Open the command palette[^1].
1. Execute `AutoSetSyntax: Migrate Settings`.
1. It should convert your v1 settings to v2 version in a new tab.
1. Copy new settings, paste them to overwrite old ones and then save.
1. Maybe, do some adjustments.
   Especially for `selector` in syntax rules if you have `working_scope` modified in v1.

## From ApplySyntax

It's theoretically mostly possible, but no automatic solution is created.

[^1]: Command palette: ++ctrl+p++ for Windows/Linux. ++cmd+p++ for macOS.
