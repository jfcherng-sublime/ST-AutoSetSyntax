# AutoSetSyntax Changelog

## 2.9.2

- chore: update guesslang server

## 2.9.1

- chore: load plugin synchronously

## 2.9.0

- chore: update guesslang server
- feat: new constraint: `is_line_count`
- refactor: bump min ST version to 4114

## 2.8.6

No change. Just to tackle with messed up versions.

## 2.8.5

- fix: syntax highlighting for log panel

## 2.8.4

- chore: tidy debug messages
- fix: empty "on_events" doesn't work as expected

## 2.8.3

- chore: change default `trim_file_size` to `20000` (about 20KB)
- chore: change default `trim_first_line_length` to `500`
- feat: debounce detection when text changes
- perf: fire `on_text_changed_async` only when syntax is plain text

## 2.8.2

- chore: update guesslang server
- chore: add `.in` into `default_trim_suffixes`

## 2.8.1

- chore: update guesslang server

## 2.8.0

- fix: guesslang on hidden file without an extension
- feat: auto set syntax for ST syntax test files

  This should be useful for those who have no file extension.

## 2.7.0

- feat: add new setting `trim_suffixes_auto`

  Apart from `trim_suffixes`, also try to remove every sub-extensions when finding a syntax match.
  For example, for the file `foo.json.ext1.ext2.ext3`, this setting enables trying the following file names as well.

  - `foo.json.ext1.ext2` (no matching syntax)
  - `foo.json.ext1` (no matching syntax)
  - `foo.json` (matches `JSON` syntax)
  - If there is no `JSON` syntax, then `foo` will be tried.

## 2.6.10

- fix: RuntimeError: dictionary changed size during iteration

## 2.6.9

- feat: treat files started with `Makefile.` as Makefile

  Such as `Makefile.build`, `Makefile.debug`, etc...

## 2.6.8

- chore: update guesslang server

## 2.6.7

- fix: `Jenkinsfile` is detected as Python
- fix: detect VIM syntax settings not only at the first line

## 2.6.6

- fix: nested MatchRules without "match" doesn't work (#11)
- refactor: get rid of ".." from path

## 2.6.5

- refactor: assume guesslang server starts if port is already in use

## 2.6.4

- chore: update language detection model

## 2.6.3

- refactor: allow manually run AI model on plain text file

## 2.6.2

- fix: `auto_set_syntax_create_new_xxx` commands not working
- fix: command name CamelCase
- refactor: simplify `boot.py`

## 2.6.1

- fix: internal states for running `ClearLogPanel` from command palette
- fix: modules should be reloaded when update plugin
- refactor: squash log messages if they are duplicate

## 2.6.0

- feat: introduce a new AI model (`vscode-regexp-languagedetection`) which comes from VSCode 1.65.0

  It will be used by default for small buffer if `guesslang.enabled` is `true`.
  To use it, you have to run `AutoSetSyntax: Download Guesslang Server` from the command palette again.

## 2.5.0

- refactor: let `guesslang` server guess JS vs TS if possible
- feat: add new constraint: `is_guesslang_enabled`
- fix: "invert" typo in `sublime-package.json`

## 2.4.4

- chore: revise menu wording
- dosc: update missing 2.4.3 changelog
- refactor: remove leading plugin name from log panel
- refactor: tidy codes

## 2.4.3

- fix: set `is_widget` for the log panel

## 2.4.2

- docs: add use case for dim out build status from the build output panel
- fix: `guesslang` server connection failed on Linux
- refactor: bundled syntaxes

## 2.4.1

- refactor: refine scope for `ExecOutput.sublime-syntax`

## 2.4.0

- feat: set default syntax for build output panel
- fix: partial path syntax representation not working

## 2.3.14

- fix: plugin is triggered before settings are ready
- refactor: make checking `guesslang` server started more clearly
- refactor: simply command `auto_set_syntax_create_new_implementation`

## 2.3.13

- fix: correct type annotation for `ExpandableVar`
- fix: various constraints give wrong results
- pref: refactor `generate_trimmed_strings()` with trie
- refactor: make `event_name` into `Enum`

## 2.3.12

- feat: add as YAML file: `.clang-format`, `.clang-tidy`, `.clangd`

## 2.3.11

- feat: add `.shared` into trimmed suffixes
- refactor: simplify codes
- test: add an PHP as xxx.sh file sample

## 2.3.10

- fix: always prefer shebang over filename
- chore: improve debug messages
- chore: update JSON rule as per ApplySytnax's

## 2.3.9

- feat: add `case_insensitive` for `is_extension` constraint
- docs: add hinting for Win7 with Node.js v14

## 2.3.8

- chore: fix outdated `sublime-package.json` contents
- feat: add a rule for ST/SM `changelog.txt`
- feat: add new constraints `is_arch`, `is_platform` and `is_platform_arch`
- fix: also try trimmed filename when triggered by a command

## 2.3.7

- feat: add a rule for `SQL`
- fix: `head_tail_content()` wrong tail content
- chore: add some debug message for guesslang

## 2.3.6

- fix: recheck view syntax again before setting syntax by guesslang

## 2.3.5

- fix: auto restart guesslang server after running install command
- fix: download guesslang server by chunks
- refactor: use hardcoded guesslang server download URL
- chore: also check guesslang server bin existence after downloading

## 2.3.4

- fix: `auto_set_syntax_download_guesslang_server` command doesn't create folder recursively

## 2.3.3

- fix: `auto_set_syntax_download_guesslang_server` command failure because files/directories are locked

## 2.3.2

- fix: do some basic checks for the guesslang-predicted syntax

  The model seems to predict some plain text as `INI` syntax quite frequently...

## 2.3.1

- fix: do not apply guesslang on files having an extension

## 2.3.0

- feat: predict syntax by a machine learning model

  This experimental feature is disabled by default.
  It provides the same feature which is introduced in VSCode 1.60.
  https://code.visualstudio.com/updates/v1_60#_automatic-language-detection
  If you want to try it, please check the following link.
  https://jfcherng-sublime.github.io/ST-AutoSetSyntax/experimental/ml-based-syntax-detection/

- chore: reduce default `trim_file_size` setting from `5000` to `4000`

## 2.2.6

- feat: add a rule for `Java`
- refactor: allow using `view_clear_undo_stack` in text commands
- refactor: use `set_read_only` to replace `command_mode`

## 2.2.5

- fix: `View.clear_undo_stack` can not be run inside `TextCommand`
- fix: some panel commands are not shown in command palette
- fix: `scope:output.autosetsyntax.log` not found during updating plugin

## 2.2.4

- fix: typo in default settings

## 2.2.3

- chore: prioritize plugin core syntax rules

  Otherwise, if the user has a bad syntax rule in user settings,
  that may make debug information always be set with a wrong syntax.

## 2.2.2

- chore: add some comments for `sublime-package.json`
- feat: add `case_insensitive` for `is_name` constraint
- feat: add a rule for `qt.conf`
- fix: `is_size` constraint has no AC in settings
- perf: speedup detecting `TypoScript`

## 2.2.1

- feat: add a rule for `qt.conf`

## 2.2.0

- fix: `parse_regex_flags()` for duplicate flags

## 2.1.11

- fix: apply a syntax via VIM modeline

## 2.1.10

- feat: add a rule for Qt's translation files
- fix: AttributeError: type object 'View' has no attribute 'clear_undo_stack'

## 2.1.9

- refactor: make `trim_suffixes` more sorted
- fix: clear undo stack for the log panel

## 2.1.8

- fix: AutoSetSyntax debug info is not auto set syntax
- refactor: generate `syntax_rules` and `trim_suffixes` more statically

## 2.1.7

- fix: set syntax during typing not working
- chore: use `JSON` for js/css source map

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

- refactor: completely rewritten to utilize ST 4 APIs and Python 3.8
- feat: users can define their `syntax` rules recursively with `match` rules and `constraint` rules
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
