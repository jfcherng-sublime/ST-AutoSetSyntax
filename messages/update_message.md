AutoSetSyntax has been updated. To see the changelog, visit
Preferences » Package Settings » AutoSetSyntax » CHANGELOG

## 2.1.0

- feat: add new constraints: `is_in_hg_repo`, `is_in_svn_repo`

## 2.0.1

- refactor: improve `is_extension` constraint
- perf: optimize `AbstractMatch.test_count()`

## 2.0.0

If you are a user from v1 with custom syntax rules,
check the [migration guide](https://jfcherng-sublime.github.io/ST-AutoSetSyntax/migration/).

- refactor: complete rewritten to utilize ST 4 APIs and Python 3.8
- feat: users can define their `syntax` rule recursively with `match` rules and `constraint` rules
- feat: plugin logs are moved to a dedicated panel
- feat: `auto_set_syntax_debug_information` command to help user dump information for debugging

For more details, visit the online documentation: https://jfcherng-sublime.github.io/ST-AutoSetSyntax/
