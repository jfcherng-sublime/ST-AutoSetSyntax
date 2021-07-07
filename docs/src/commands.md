--8<-- "refs.md"

# Commands

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
        "caption": "AutoSetSyntax: Create New Constrant",
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

## Migration

### `auto_set_syntax_migrate_settings`

!!! example

    ```js
    {
        "caption": "AutoSetSyntax: Migrate Settings",
        "command": "auto_set_syntax_migrate_settings",
    },
    ```

    At this moment, this command only works if the current view content is AutoSetSyntax v1 settings.
    It will convert it into a v2 settings and put the result in a new view.

## Logging

### `auto_set_syntax_toogle_log_panel`

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
