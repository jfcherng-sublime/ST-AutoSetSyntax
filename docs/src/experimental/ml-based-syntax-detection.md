# Machine Learning Based Syntax Detection

--8<-- "refs.md"

!!! warning "This feature is experimental and disabled by default."

## Overview

It uses machine learning models from VSCode to predict the syntax of codes.

## Prerequisites

1. [Node.js][node.js] ≥ 16


    - If the directory of your `node` executable is in the `PATH` environment variable, then you don't have to configure it.
    - If your Node runtime is provided by `lsp_utils`, then you can config `"guesslang.node_bin"` to `"${lsp_utils_node_bin}"`.
    - If you are none of the above cases, you have to provide the path of your `node` executable in `"guesslang.node_bin"`.

        !!! Tip "Windows 7 Users"

            The official Node.js v16 installer won't work on Windows 7 but you can simply download a
            [portable](https://nodejs.org/dist/latest-v16.x/) version such as `node-v16.20.2-win-x64.zip`,
            decompress it and set the `guesslang.node_bin` path.

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
