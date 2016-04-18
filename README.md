Sublime-AutoSetSyntax
============================

This repository is a plugin for Sublime Text 3.
It automatically sets the syntax for your file if an event is triggered.
The original thought is from [here](https://forum.sublimetext.com/t/automatically-set-view-syntax-according-to-first-line/18629).


Examples
========

### PHP Tag

![](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetSyntax/gh-pages/images/example/php-tag.gif)

0. Create a new tab.
0. Type `<?php`.
0. The syntax will be set to PHP automatically. (triggered by `on_modified_async`)

### Colored Git Log

![](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetSyntax/gh-pages/images/example/git-log.gif)

0. Prerequisites: [ANSIescape](https://packagecontrol.io/packages/ANSIescape) and [SideBarGit](https://packagecontrol.io/packages/SideBarGit).
0. Set your colored git log command. I personally set `git config --global alias.l "log --graph --date=short --pretty=format:'%C(yellow bold)%h%Creset%C(auto)%d%Creset - %s %C(green bold)[%an]%Creset %C(blue bold)(%ad, %cr)%Creset'"`.
0. Add `"ANSIescape/ANSI.tmLanguage": ["^\\s*\\[SideBarGit@.*\\] git l\\b"]` to `syntax_mapping`.
0. Add `source.diff` to `working_scope` like `"working_scope": "(?x)^(text.plain | source.diff)\\b"`.
0. Execute your customized git log command. In this example, it is `git l` as set in the previous step.
0. The output syntax will be set to ANSI which provides ANSI color rendering. (triggered by `on_modified_async`)

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
        "PHP/PHP": [
            "<\\?php",
            ...
        ],
        ...
    },
    "working_scope": "^text.plain\\b"
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
      "CRITICAL" (very few), "ERROR", "WARNING", "INFO", "DEBUG" (most tedious) and "NOTHING" (nothing).
- syntax_mapping
    - key: The partial path of a syntax file. Of course, you can use a full path like `Packages/PHP/PHP.sublime-syntax`.
    - value: Regular expressions to match the first line.
- working_scope
    - The scope that this plugin should work (regular expression). Leave it blank to match any scope.


Commands
========

You may disable all `event_listeners` in your user settings and add a key binding to set syntax.

```javascript
{ "keys": ["ctrl+alt+s", "ctrl+alt+s"], "command": "auto_set_syntax" },
```


How It Works
============

When this plugin is loaded:

0. Read all syntax definition files.
0. Try to find `first_line_match` in `.sublime-syntax`s (if ST >= 3084) and `firstLineMatch` in `.tmLanguage`s.
0. Merge `syntax_mapping` with results from the previous step.

When an event is triggered:

0. May check conditions like cursor counts, cursor position and etc...
0. Make sure `working_scope` matches the scope of the first character.
0. Call command `auto_set_syntax`.

When command `auto_set_syntax` is called:

0. Match the first line with results we found while loading plugin.
0. If there is any luck, set the corresponding syntax for the user.


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


License
=======

The MIT License (MIT)

Copyright (c) 2016 Jack Cherng

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
