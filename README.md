Sublime-AutoSetSyntax
============================

This repository is a plugin for Sublime Text 3.
It automatically sets the syntax for your file if an event is triggered.
The original thought comes from [here](https://forum.sublimetext.com/t/automatically-set-view-syntax-according-to-first-line/18629).


Examples
========

### Guess the Syntax After Stripping Unimportant File Extensions

![](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetSyntax/gh-pages/images/example/try-strip-file-exts.gif)

1. `config_gitlab.yml.example` -> `config_gitlab.yml` -> Ah! `.yml` should use the `YAML` syntax.
1. See `try_filename_remove_exts` settings for details.


### PHP Tag

![](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetSyntax/gh-pages/images/example/php-tag.gif)

1. Create a new tab.
1. Type `<?php`.
1. The syntax will be set to PHP automatically. (triggered by `on_modified_async`)


### Colored Git Log

![](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetSyntax/gh-pages/images/example/git-log.gif)

1. Prerequisites: [ANSIescape](https://packagecontrol.io/packages/ANSIescape) and [SideBarGit](https://github.com/titoBouzout/SideBarGit).
1. Set your colored git log command. I personally set `git config --global alias.l "log --graph --date=short --color --pretty=format:'%C(yellow bold)%h%Creset%C(auto)%d%Creset - %s %C(green bold)[%an]%Creset %C(blue bold)(%ad, %cr)%Creset'"`.
1. Add `"ANSIescape/ANSI.tmLanguage": ["^\\s*\\[SideBarGit@.*\\] git l\\b"]` to `syntax_mapping`.
1. Add `source.diff` to `working_scope` like `"working_scope": "(?x)^(text.plain | source.diff)\\b"`.
1. Execute your customized git log command. In this example, it is `git l` as set in the previous step.
1. The output syntax will be set to ANSI which provides ANSI color rendering. (triggered by `on_modified_async`)


### More Creative Usages To Share?

Feel free to create an issue or a pull request.


User Settings
=============

```javascript
{
    "event_listeners": {
        "on_activated_async": true,
        "on_clone_async": true,
        "on_load_async": true,
        "on_modified_async": true,
        "on_new_async": true,
        "on_post_paste": true,
        "on_pre_save_async": true,
    },
    "first_line_length_max": 80,
    "log_level": "INFO",
    "syntax_mapping": {
        "PHP/PHP.": [
            "<\\?php",
            ...
        ],
        ...
    },
    "working_scope": "^text.plain\\b",
    "try_filename_remove_exts": [
        ".backup",
        ".bak",
        ".default",
        ".dist",
        ".example",
        ".inc",
        ".include",
        ".local",
        ".sample",
    ],
}
```

- event_listeners
    - on_activated_async": Called when a view gains input focus.
    - on_clone_async": Called when a view is cloned from an existing one.
    - on_load_async": Called when the file is finished loading.
    - on_modified_async": Called after changes have been made to a view.
    - on_new_async": Called when a new buffer is created.
    - on_post_paste": Called after there is a paste operation.
    - on_pre_save_async": Called just before a view is saved.
- first_line_length_max
    - \>= 0: The maximum length to lookup in the first line.
    - < 0: No limitation.
- log_level
    - Determine how detailed log messages are. The value could be
      "CRITICAL" (very few), "ERROR", "WARNING", "INFO", "DEBUG" (most detailed) and "NOTHING" (nothing).
- syntax_mapping
    - key: The partial path of a syntax file. Of course, you can use a full path like `Packages/PHP/PHP.sublime-syntax`.
    - value: Regular expressions to match the first line.
- working_scope
    - The scope that this plugin should work (regular expression). Leave it blank to match any scope.
- try_filename_remove_exts
    - For `text.plain` scope, try to remove these file extensions from the file name
      and may set a syntax corresponding syntax by the stripped file name.


Commands
========

You may disable all `event_listeners` in your user settings and add a key binding to set syntax.

```javascript
{ "keys": ["ctrl+alt+s", "ctrl+alt+s"], "command": "auto_set_syntax" },
```


How It Works
============

When this plugin is loaded:

1. Read all syntax definition files.
1. Try to find `first_line_match` in `.sublime-syntax`s (if ST >= 3084) and `firstLineMatch` in `.tmLanguage`s.
1. Merge `syntax_mapping` with results from the previous step.

When an event is triggered:

1. May check conditions like cursor counts, cursor position and etc...
1. Make sure `working_scope` matches the scope of the first character.
1. Call command `auto_set_syntax`.

When command `auto_set_syntax` is called:

1. Match the first line with results we found while loading plugin.
1. If there is any luck, set the corresponding syntax for the user.


Debug
=====

Debug messages are printed to your Sublime Text console (<kbd>Ctrl</kbd>+<kbd>`</kbd>), which looks like

```
AutoSetSyntax: [ERROR] regex compilation failed in user settings "working_scope": ^text.plain\b+
AutoSetSyntax: [WARNING] "event_listeners -> on_pre_save_async" is not set in user settings (assumed true)
AutoSetSyntax: [INFO] match syntax file "php-grammar/PHP." with "Packages/php-grammar/PHP.sublime-syntax"
```


See Also
========

- [ApplySyntax](https://github.com/facelessuser/ApplySyntax)


Supporters <a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=ATXYY9Y78EQ3Y" target="_blank"><img src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif" /></a>
==========

Thank you guys for sending me some cups of coffee.
