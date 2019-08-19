# Sublime-AutoSetSyntax

<a href="https://packagecontrol.io/packages/AutoSetSyntax"><img alt="Package Control" src="https://img.shields.io/packagecontrol/dt/AutoSetSyntax"></a>
<a href="https://github.com/jfcherng/Sublime-AutoSetSyntax/tags"><img alt="GitHub tag (latest SemVer)" src="https://img.shields.io/github/tag/jfcherng/Sublime-AutoSetSyntax?logo=github"></a>
<a href="https://github.com/jfcherng/Sublime-AutoSetSyntax/blob/master/LICENSE"><img alt="Project license" src="https://img.shields.io/github/license/jfcherng/Sublime-AutoSetSyntax?logo=github"></a>
<a href="https://github.com/jfcherng/Sublime-AutoSetSyntax/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/jfcherng/Sublime-AutoSetSyntax?logo=github"></a>
<a href="https://www.paypal.me/jfcherng/5usd" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-blue.svg?logo=paypal" /></a>

This plugin automatically sets the syntax for your file if possible.
The original thought comes from [here](https://forum.sublimetext.com/t/automatically-set-view-syntax-according-to-first-line/18629).


## Installation

This package is available on Package Control by the name of [AutoSetSyntax](https://packagecontrol.io/packages/AutoSetSyntax).


## Examples

<details><summary>Guess the Syntax After Stripping Unimportant File Extensions</summary>

![](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetSyntax/gh-pages/images/example/try-strip-file-exts.gif)

1. `config_gitlab.yml.example` -> `config_gitlab.yml` -> Ah! `.yml` should use the `YAML` syntax.
1. See `try_filename_remove_exts` settings for details.

</details>

<details><summary>PHP Tag</summary>

![](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetSyntax/gh-pages/images/example/php-tag.gif)

1. Create a new tab.
1. Type `<?php`.
1. The syntax will be set to PHP automatically. (triggered by `on_modified_async`)

</details>

<details><summary>Colored Git Log</summary>

![](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetSyntax/gh-pages/images/example/git-log.gif)

1. Prerequisites: [ANSIescape](https://packagecontrol.io/packages/ANSIescape) and [SideBarGit](https://github.com/titoBouzout/SideBarGit).
1. Set your colored git log command. I personally set `git config --global alias.l "log --graph --date=short --color --pretty=format:'%C(yellow bold)%h%Creset%C(auto)%d%Creset - %s %C(green bold)[%an]%Creset %C(blue bold)(%ad, %cr)%Creset'"`.
1. Add `"ANSIescape/ANSI.tmLanguage": ["^\\s*\\[SideBarGit@.*\\] git \\b"]` to `syntax_mapping`.
1. Add `source.diff` to `working_scope` like `"working_scope": "(?x)^(text.plain | source.diff)\\b"`.
1. Execute your customized git log command. In this example, it is `git l` as set in the previous step.
1. The output syntax will be set to ANSI which provides ANSI color rendering. (triggered by `on_modified_async`)

</details>


### More Creative Usages To Share?

Feel free to create an issue or a pull request.


## User Settings

<details><summary>Click to expand</summary>

```javascript
{
    // When should this plugin work?
    "event_listeners": {
        // called when a view gains input focus
        "on_activated_async": true,
        // called when a view is cloned from an existing one
        "on_clone_async": true,
        // called when the file is finished loading
        "on_load_async": true,
        // called after changes have been made to a view
        "on_modified_async": true,
        // called when a new buffer is created
        "on_new_async": true,
        // called after there is a paste operation
        "on_post_paste": true,
        // called just before a view is saved
        "on_pre_save_async": true,
    },
    // The max lookup length for the first line.
    // A negative number means no limitation.
    "first_line_length_max": 80,
    // How detailed log messages should be?
    // "CRITICAL" (very few), "ERROR", "WARNING", "INFO", "DEBUG" (most tedious) or "NOTHING" (no log)
    "log_level": "INFO",
    /**
     * The syntax maaping rules.
     *
     * @key The partial (or full) resource path of a syntax file.
     * @value Regexes to match the first line.
     */
    "syntax_mapping": {
        // "Packages/PHP/PHP.sublime-syntax": [
        //     "<\\?php",
        //     "<\\?=",
        // ],
    },
    // The partial (or full) resource path of the syntax file used when creating a new file.
    // Nothing would happen if this is a empty string.
    "new_file_syntax": "",
    // The scope that this plugin should work (regex).
    // Leave it blank will result in matching any scope.
    "working_scope": "^text\\.plain\\b",
    // Try to remove these file extensions from the file name
    // so a syntax may be assigned due to a stripped file name.
    "try_filename_remove_exts": [
        "-dev",
        "-development",
        "-dist",
        "-prod",
        "-production",
        "-test",
        ".backup",
        ".bak",
        ".default",
        ".dist",
        ".example",
        ".inc",
        ".include",
        ".local",
        ".sample",
        ".test",
        ".tpl",
    ],
}
```

</details>


## Commands

You may disable all `event_listeners` in your user settings and add a key binding to set syntax.

```javascript
{ "keys": ["ctrl+alt+s", "ctrl+alt+s"], "command": "auto_set_syntax" },
```


## How It Works

When this plugin is loaded:

1. Construct the syntax mappings.

   1. Read all syntax definition files.
   1. Try to find following informations.

      - `first_line_match` in `.sublime-syntax`s and `firstLineMatch` in `.tmLanguage`s.
      - `file_extensions` in `.sublime-syntax`s and `fileTypes` in `.tmLanguage`s.

   1. Merge `syntax_mapping` with results from the previous step.

1. If the scope is `text.plain`, try to remove some extensions from the file name basing on `try_filename_remove_exts`.
   A syntax may be assigned due to a stripped file name matches.

When an event is triggered:

1. May check conditions like cursor counts, cursor position and etc...
1. Make sure `working_scope` matches the scope of the first character.
1. Call command `auto_set_syntax`.

When command `auto_set_syntax` is called:

1. Match extensions with the file name.
1. Match the first line with file content.
1. If there is any luck, set the corresponding syntax for the user.


## Debug

Debug messages are printed to your Sublime Text console (<kbd>Ctrl</kbd>+<kbd>\`</kbd>), which looks like

```
AutoSetSyntax: [ERROR] regex compilation failed in user settings "working_scope": ^text.plain\b+
AutoSetSyntax: [WARNING] "event_listeners -> on_pre_save_async" is not set in user settings (assumed true)
AutoSetSyntax: [INFO] match syntax file "php-grammar/PHP." with "Packages/php-grammar/PHP.sublime-syntax"
```


## See Also

- [ApplySyntax](https://github.com/facelessuser/ApplySyntax)
