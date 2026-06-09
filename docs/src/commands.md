# Commands

--8<-- "refs.md"

## Main

### `auto_set_syntax`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Auto Set Syntax",
        "command": "auto_set_syntax",
    },
    ```

    This command tries to set the syntax for the current view.

    !!! info

        You may consider AutoSetSyntax is kind of working in a way that it checks
        some prerequisites and triggers the `auto_set_syntax` command automatically.
        Although actually, AutoSetSyntax doesn't trigger the command.

## Implementation

### `auto_set_syntax_create_new_constraint`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Create New Constraint",
        "command": "auto_set_syntax_create_new_constraint",
    },
    ```

    This command creates a template for a new `Constraint` implementation.

### `auto_set_syntax_create_new_match`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Create New Match",
        "command": "auto_set_syntax_create_new_match",
    },
    ```

    This command creates a template for a new `Match` implementation.

## Utilities

### `auto_set_syntax_download_dependencies`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Download Dependencies",
        "command": "auto_set_syntax_download_dependencies",
    },
    ```

    This command downloads the Magika deep-learning detection dependencies.
    It is the first step of the [Magika setup guide][plugin-magika].

### `auto_set_syntax_syntax_rules_summary`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Syntax Rules Summary",
        "command": "auto_set_syntax_syntax_rules_summary",
    },
    ```

    This command outputs a summary of all compiled syntax rules for debugging.

## Logging

### `auto_set_syntax_toggle_log_panel`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Toggle Log Panel",
        "command": "auto_set_syntax_toggle_log_panel",
    },
    ```

    This command toggles the AutoSetSyntax log panel for the current window.

### `auto_set_syntax_clear_log_panel`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Clear Log Panel",
        "command": "auto_set_syntax_clear_log_panel",
    },
    ```

    This command clears the AutoSetSyntax log panel for the current window.

## Debugging

### `auto_set_syntax_debug_information`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Debug Information",
        "command": "auto_set_syntax_debug_information",
    },
    ```

    This command copies information for debugging to the clipboard.
    Check "[Debug][plugin-debug]" for more details.
