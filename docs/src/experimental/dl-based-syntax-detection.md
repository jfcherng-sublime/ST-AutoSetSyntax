# Deep Learning Based Syntax Detection

--8<-- "refs.md"

!!! warning "This feature is experimental and disabled by default."

## Overview

It uses Google's [Magika](https://github.com/google/magika) library to detect the file syntax.

## Prerequisites

1.  If you are using MacOS, the minimum supported OS version is MacOS 11 (Big Sur).

1.  Install dependencies.

    Run `AutoSetSyntax: Download Dependencies` from the command palette.
    The dependencies can be up to 50 MB in size, so it may take a while.
    When it's done, there will be a popup dialogue.

1.  Enable the feature.

    Set `"magika.enabled"` to `true` in AutoSetSyntax's settings.

After you've done all steps above, it should just work without restarting Sublime Text.

## Demo

<video controls="controls" style="max-width:100%">
  <source type="video/mp4" src="https://user-images.githubusercontent.com/6594915/133069990-ea6eaf22-f341-4c0c-9b74-1931f96c7183.mp4"></source>
  <p>Your browser does not support the video element.</p>
</video>
