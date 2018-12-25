AutoSetSyntax has been updated. To see the changelog, visit
Preferences » Package Settings » AutoSetSyntax » Changelog

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
