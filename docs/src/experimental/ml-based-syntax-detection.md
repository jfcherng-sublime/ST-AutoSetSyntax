--8<-- "refs.md"

# Machine Learning Based Syntax Detection

!!! warning "This feature is experimental and disabled by default."

## Overview

This provides the same feature which is introduced in [VSCode 1.60][vscode-changelog-1_60].
It uses a machine learning model to predict a syntax for the codes in [this][vscode-languagedetection] VSCode plugin.
The model used in VSCode is run with Node.js. AutoSetSyntax further wraps it as a websocket server
and communicates with it in Sublime Text.

!!! Info

    If you are interested in more details, you may read VSCode's developer
    discussed with [Guesslang][guesslang-repo]'s author [here][guesslang-vscode-discussion].

## Prerequisites

- Node.js >= 14

    If the directory of your `node` executable is in the `PATH` environment variable, then you don't have to configure it.
    If your Node runtime is provided by `lsp_utils`, then you can config `"guesslang.node_bin"` to `"${lsp_utils_node_bin}"`.
    If you are none of the above cases, you have to provide the path of your `node` executable in `"guesslang.node_bin"`.
  
    !!! Tip "For Windows 7 Users"

        Windows 7 can't install Node.js v14 but you can simply download a [portable version](https://nodejs.org/dist/latest-v14.x/)
        such as `node-v14.17.6-win-x64.zip`, decompress it and set the `guesslang.node_bin` path.

- Install the guesslang server.

    Run `AutoSetSyntax: Download Guesslang Server` from the command palette. It will popup a dialogue when it's done.

- Enable the feature.

    Set `"guesslang.enabled"` to `true` in AutoSetSyntax's settings.

After you've done all steps above and then restart ST, it should work after a few seconds.

## Demo

<video controls="controls" style="max-width:100%">
  <source type="video/mp4" src="https://user-images.githubusercontent.com/6594915/133069990-ea6eaf22-f341-4c0c-9b74-1931f96c7183.mp4"></source>
  <p>Your browser does not support the video element.</p>
</video>

[guesslang-repo]: https://github.com/yoeo/guesslang
[guesslang-vscode-discussion]: https://github.com/yoeo/guesslang/issues/29
[vscode-changelog-1_60]: https://code.visualstudio.com/updates/v1_60#_automatic-language-detection
[vscode-languagedetection]: https://github.com/Microsoft/vscode-languagedetection
