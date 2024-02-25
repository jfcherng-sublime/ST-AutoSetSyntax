# Deep Learning Based Syntax Detection

--8<-- "refs.md"

!!! warning "This feature is experimental and disabled by default."

## Overview

It uses Google's [Magika](https://github.com/google/magika) library to detect the file syntax.

## Prerequisites

1.  If you are using MacOS, the minimum supported OS version is MacOS 11 (Big Sur).

1.  Install dependencies.

    Run `AutoSetSyntax: Download Dependencies` from the command palette.
    The dependencies can be up to \~50 MB in size, so it may take a while.
    When it's done, there will be a popup dialogue.

    !!! tip "If your machine have no access to GitHub..."

        You can download the dependencies on [GitHub][plugin-dependencies-dir]
        basing on your machine's OS and CPU architecture by any means.
        If you don't know which one to download, run the following command in Sublime Text's console:

        ```python
        import AutoSetSyntax; AutoSetSyntax.plugin.constants.PLUGIN_PY_LIBS_URL
        ```
        
        Decompress the downloaded ZIP file into `Package Storage/AutoSetSyntax/`
        so that the directory structure looks like the following:

        ```text
        Package Storage
        └─ AutoSetSyntax
           └─ libs-py38@linux_x64
              ├── click
              ├── click-8.1.7.dist-info
              ├── colorama
              ├── colorama-0.4.6.dist-info
              ├── coloredlogs
              ├── coloredlogs.pth
              ├── coloredlogs-15.0.1.dist-info
              ...
        ```

        You can open `Package Storage/AutoSetSyntax/` directory by running
        the following Python code in Sublime Text's console:

        ```python
        import AutoSetSyntax; (d := AutoSetSyntax.plugin.constants.PLUGIN_STORAGE_DIR).mkdir(parents=True, exist_ok=True); window.run_command("open_dir", {"dir": str(d)})
        ```

1.  Enable the feature.

    Set `"magika.enabled"` to `true` in AutoSetSyntax's settings.

After finishing all steps above, it should just work without restarting Sublime Text.
You may go [here](https://doc.rust-lang.org/rust-by-example/hello.html) to copy some Rust codes
and paste them into Sublime Text to test whether this feature works.

## Demo

<video controls="controls" style="max-width:100%">
  <source type="video/mp4" src="https://user-images.githubusercontent.com/6594915/133069990-ea6eaf22-f341-4c0c-9b74-1931f96c7183.mp4"></source>
  <p>Your browser does not support the video element.</p>
</video>
