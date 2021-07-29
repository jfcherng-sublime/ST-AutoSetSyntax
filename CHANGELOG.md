# AutoSetSyntax

## 2.1.6

- fix: auto trimmed filename should only works on plain text

## 2.1.5

- fix: overkill changing `.erb` files back to `HTML` syntax

## 2.1.4

- feat: add `lua` syntax rule
- feat: improve `is_interpreter` to match VIM's syntax line

## 2.1.3

- feat: add `Diff`, `JavaScript` syntax rules
- feat: add `threshold` `kwargs` for `contains` and `contains_regex`
- chore: update `matlab` syntax rule

## 2.1.2

- feat: add `C#` syntax rule

## 2.1.1

- feat: add `C++` syntax rule

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

## 1.10.14

- refactor: run the whole `plugin_load()` async

## 1.10.13

- fix: logger level names for Python 3.8

## 1.10.12

- chore: auto set Package Control messages to Markdown

## 1.10.11

- fix: plugin may be not prepared yet

## 1.10.10

- refactor: improve the logic to get the first line
- fix: plugin may be not prepared yet

## 1.10.9

- perf: run time-consuming codes asynchronously

## 1.10.8

- fix: should not activate this plugin on widgets

## 1.10.7

- revert: Revert "Add .python-version for ST4"

  This plugin depends on "pyyaml" module, which is not available
  (Python 3.8) via package control at this moment.

## 1.10.6

- Let `Plain Text` be the last choice.
  This makes `requirements.txt-optional` able to be detected as `requirements.txt`
  and have syntax highlighting if there is a syntax for it.

- Add "-optional" into `try_filename_remove_exts`.

## 1.10.5

- Add ".orig" to `try_filename_remove_exts`.
- Fix changing log level won't have effect immediately.

## 1.10.4

- Add "-dist" to `try_filename_remove_exts`.
- Workaround inline regex flags (such as `(?x: ... )`) are not supported by Python 3.3.
- Workaround some syntax files that are unable to parse before.
- Fix log messages appear twice in ST's console.
- Improved log messages.
- Some refactor.

## 1.10.3

- Put menu files to `menus/`.
- Update `try_filename_remove_exts`.

  Add "-dev", "-development", "-prod", "-production", "-test", ".test", ".tpl".

## 1.10.2

- Add the command to the command palette.

## 1.10.1

- Use a new side-by-side window to edit settings.

## 1.10.0

- New feature: Auto set syntax when creating a new file.

  See the "new_file_syntax" settings.

## 1.9.1

- Remove debugging codes.

## 1.9.0

- New feature: Auto set syntax by stripping file extensions.

  When opening a default configuration file like `config.js.dist`.
  Because there is no syntax for a `.js.dist` file or a `.dist` file,
  the file will be opened as plain text without syntax highlighting.

  This feature tries to remove some common unimportant extensions such as `.dist`, `.sample`, ... etc
  from the file name. And test the stripped file name `config.js` with
  syntax definitions and applies `Javascript` syntax to it.

  You could define extensions which would be tried to be removed in the
  `try_filename_remove_exts` settings.

## 1.8.7

- Just some directory structure tweaks.

## 1.8.6

- Fix autocomplete is triggered in quick panel & search panel (#3)

## 1.8.5

- Add config for `"log_level": "NOTHING"`.
  `"NOTSET"` is not what I just thought. So add my own `"log_lovel": "NOTHING"`.

## 1.8.4

- Load yaml module by Package Control `dependencies.json`.
- Move SyntaxMappings.py into a sub-directory.

## 1.8.3

- Correct the usage of `settings.add_on_change()`.

## 1.0.1 ~ 1.8.2

- Lost histories...

## 1.0.0

- Initial release.
