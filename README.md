Sublime-AutoSetNewFileSyntax
============================
This repository is a plugin for Sublime Text >= 3084. 
It automatically sets the syntax for plain text content while typing its first line. 
The original thought is from [here](https://forum.sublimetext.com/t/automatically-set-view-syntax-according-to-first-line/18629).


Examples
========
![example](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetNewFileSyntax/gh-pages/images/example.gif)

If we create a new file in Sublime Text and type `<?php`, this plugin will set the syntax to PHP automatically.


User Settings
=============
```javascript
{
    "first_line_length_max": 80,
    "syntax_mapping": {
        "PHP/PHP": [
            "<\\?php",
            ...
        ],
        ...
    },
    "event_listeners": {
        "on_activated_async": true,
        "on_clone_async": true,
        "on_load_async": true,
        "on_modified_async": true,
        "on_new_async": true,
        "on_pre_save_async": true,
    }
}
```

- first_line_length_max
    - \>= 0: The maximum length to lookup in the first line.
    - < 0: No limitation.
- syntax_mapping
    - key: The partial path of syntax file. Of course, you can use a full path like `Packages/PHP/PHP.sublime-syntax`.
    - value: Regular expressions to match the first line.
- event_listeners
    - on_activated_async": Called when a view gains input focus.
    - on_clone_async": Called when a view is cloned from an existing one.
    - on_load_async": Called when the file is finished loading.
    - on_modified_async": Called after changes have been made to a view.
    - on_new_async": Called when a new buffer is created.
    - on_pre_save_async": Called just before a view is saved.


How It Works
============
When the plugin is loaded:

0. Read all syntax definition files.
0. Try to find `first_line_match` in `.sublime-syntax`s and `firstLineMatch` in `.tmLanguage`s.

When the first line of a plain text file is being edited:

0. Match the first line with results we found in the previous step.
0. If there is any luck, set the corresponding syntax for the user.


Debug
=====
Debug messages are printed to your Sublime Text console (<kbd>Ctrl</kbd>+<kbd>`</kbd>), which looks like
```
AutoSetNewFileSyntax: [INFO] match syntax file php-grammar/PHP. with Packages/php-grammar/PHP.sublime-syntax
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

