AutoSetSyntax has been updated. To see the changelog, visit
Preferences » Package Settings » AutoSetSyntax » CHANGELOG

## 2.6.1

- feat: introduce a new AI model (`vscode-regexp-languagedetection`) which comes from VSCode 1.65.0

  It will be used by default for small buffer if `guesslang.enabled` is `true`.
  To use it, you have to run `AutoSetSyntax: Download Guesslang Server` from the command palette again.

- fix: internal states for running `ClearLogPanel` from command palette
- refactor: squash log messages if they are duplicate
