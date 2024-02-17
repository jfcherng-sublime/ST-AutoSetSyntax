# Machine Learning Based Syntax Detection

--8<-- "refs.md"

!!! warning "This feature has been deprecated and will be removed in AutoSetSyntax v3."

## Overview

It uses machine learning models from VSCode to predict the syntax of codes.

## Prerequisites

1. [Node.js][node.js] ≥ 16

    Node.js is searched under the following order:

    - User specified path (i.e., `guesslang.node_bin`)
    - Sublime Text's `lsp_utils`-managed Node.js/Electron
    - `electron` (i.e., the executable of Electron)
    - `node` (i.e., the executable of Node.js)
    - `code` (i.e., the executable of VS Code)
    - `VSCodium` (i.e., the executable of VSCodium)

    !!! Tip "Windows 7 Users"

        The official Node.js v16 installer won't work on Windows 7 but you can simply download a
        [portable](https://nodejs.org/dist/latest-v16.x/) version such as `node-v16.20.2-win-x64.zip`,
        decompress it and set `guesslang.node_bin` (or add its directory into the `PATH` environment variable).

1. Install the server.

    Run `AutoSetSyntax: Download Guesslang Server` from the command palette. It will popup a dialogue when it's done.

1. Enable the feature.

    Set `"guesslang.enabled"` to `true` in AutoSetSyntax's settings.

After you've done all steps above and then restart ST, it should work after a few seconds.

## Demo

<video controls="controls" style="max-width:100%">
  <source type="video/mp4" src="https://user-images.githubusercontent.com/6594915/133069990-ea6eaf22-f341-4c0c-9b74-1931f96c7183.mp4"></source>
  <p>Your browser does not support the video element.</p>
</video>
