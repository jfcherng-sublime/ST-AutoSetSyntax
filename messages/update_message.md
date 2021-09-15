AutoSetSyntax has been updated. To see the changelog, visit
Preferences » Package Settings » AutoSetSyntax » CHANGELOG

## 2.3.0

- feat: predict syntax by a machine learning model

  This experimental feature is disabled by default.
  It provides the same feature which is introduced in VSCode 1.60.
  https://code.visualstudio.com/updates/v1_60#_automatic-language-detection
  If you want to try it, please check the following link.
  https://jfcherng-sublime.github.io/ST-AutoSetSyntax/experimental/ml-based-syntax-detection/

- chore: reduce default `trim_file_size` setting from `5000` to `4000`

## 2.0.0

If you are a user from v1 with custom syntax rules,
check the [migration guide](https://jfcherng-sublime.github.io/ST-AutoSetSyntax/migration/).

- refactor: complete rewritten to utilize ST 4 APIs and Python 3.8
- feat: users can define their `syntax` rule recursively with `match` rules and `constraint` rules
- feat: plugin logs are moved to a dedicated panel
- feat: `auto_set_syntax_debug_information` command to help user dump information for debugging

For more details, visit the online documentation: https://jfcherng-sublime.github.io/ST-AutoSetSyntax/
