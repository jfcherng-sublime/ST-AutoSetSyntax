# AutoSetSyntax


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
