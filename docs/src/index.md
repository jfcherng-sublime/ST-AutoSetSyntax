--8<-- "refs.md"

# AutoSetSyntax

[![Required ST Build](https://img.shields.io/badge/ST-4105+-orange.svg?style=flat-square&logo=sublime-text)](https://www.sublimetext.com)
[![GitHub Actions](https://img.shields.io/github/workflow/status/jfcherng-sublime/ST-AutoSetSyntax/Python?style=flat-square)](https://github.com/jfcherng-sublime/ST-AutoSetSyntax/actions)
[![Package Control](https://img.shields.io/packagecontrol/dt/AutoSetSyntax?style=flat-square)](https://packagecontrol.io/packages/AutoSetSyntax)
[![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/jfcherng-sublime/ST-AutoSetSyntax?style=flat-square&logo=github)](https://github.com/jfcherng-sublime/ST-AutoSetSyntax/tags)
[![Project license](https://img.shields.io/github/license/jfcherng-sublime/ST-AutoSetSyntax?style=flat-square&logo=github)](https://github.com/jfcherng-sublime/ST-AutoSetSyntax/blob/master/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/jfcherng-sublime/ST-AutoSetSyntax?style=flat-square&logo=github)](https://github.com/jfcherng-sublime/ST-AutoSetSyntax/stargazers)
[![Donate to this project using Paypal](https://img.shields.io/badge/paypal-donate-blue.svg?style=flat-square&logo=paypal)](https://www.paypal.me/jfcherng/5usd)

!!! note ""

    AutoSetSyntax v2 utilizes ST 4 plugin APIs along with Python 3.8.

## Overview

AutoSetSyntax helps you set the syntax for a view automatically in various ways:

- Default syntax for new files.
- Detecting the syntax when modifying the file.
- Trimming unimportant suffixes from the filename.
- Assigning syntax by the first line.
- User-defined rules.
- (Experimental) Machine learning based syntax detection.

If you want to learn more details, read "[Use Cases][plugin-use-cases]" and "[Configurations][plugin-configurations]".

## Installation

This package is available on [Package Control][package-control] by the name of [AutoSetSyntax][pc-autosetsyntax].

!!! success "Best Practice"

    It's strongly recommended to install [LSP][pc-lsp] and [LSP-json][pc-lsp-json] to have a better experience
    for editing settings. At least, it will provide autocompletion and verification for settings of this plugin.

## Acknowledgment

- Plugin's original idea comes from "[Automatically set view syntax according to first line][applysyntax-v1-idea]".
- [ApplySyntax][pc-applysyntax], which AutoSetSyntax v2 is inspired by.

## License

!!! quote

    --8<-- "../../../LICENSE"
