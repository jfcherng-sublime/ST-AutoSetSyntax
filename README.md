Sublime-AutoSetNewFileSyntax
============================
This repository is a plugin for Sublime Text >= 3084. 
It automatically sets the syntax for a plain text content depends on its first line. 
The original thought is from [here](https://forum.sublimetext.com/t/automatically-set-view-syntax-according-to-first-line/18629).


Examples
========
![example](https://raw.githubusercontent.com/jfcherng/Sublime-AutoSetNewFileSyntax/gh-pages/images/example.gif)

If we create a new file in Sublime Text and type `<?php`, this plugin will set the syntax to PHP automatically.


How It Works
============
0. Read all syntax definition files.
0. Try to find `first_line_match` in `.sublime-syntax`s and `firstLineMatch` in `.tmLanguage`s.
0. Match the first line with results we found in the last step.
0. If there is any luck, set the corresponding syntax for the user.


Future Works
============
- Let user add their own `first_line_match` and the corresponding syntax pairs.


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

