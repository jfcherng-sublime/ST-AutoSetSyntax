--8<-- "refs.md"

# Configurations

## Settings

Sometimes, a good way to learn about settings is reading an existing one.

??? example "AutoSetSyntax.sublime-settings"

    ```js
    --8<-- "../../../AutoSetSyntax.sublime-settings"
    ```

### `enable_log`

| Type      | Default |
| --------- | ------- |
| `boolean` | `true`  |

This setting control whether this plugin creates a dedicated log message panel.
Since the panel won't affect other plugins, the default value is `true`.

### `exec_file_syntax`

| Type     | Default                                                       |
| -------- | ------------------------------------------------------------- |
| `string` | `"Packages/AutoSetSyntax/syntaxes/ExecOutput.sublime-syntax"` |

This setting controls what syntax a build output should use. The value can be any of the followings:

- An empty string, which does nothing.
- A [syntax representation][plugin-syntax-representations].

### `new_file_syntax`

| Type     | Default |
| -------- | ------- |
| `string` | `""`    |

This setting controls what syntax a new file should use. The value can be any of the followings:

- An empty string, which does nothing.
- A [syntax representation][plugin-syntax-representations].

### `run_on_startup_views`

| Type      | Default |
| --------- | ------- |
| `boolean` | `false` |

This setting controls whether you want to run the `auto_set_syntax` command on views
which exist before the plugin is loaded. If ST starts from cold start, this settings is
necessary to set syntax for the just opened file.

!!! info

    When ST starts up, there may be views that exists before plugins are loaded.
    Those views won't trigger `on_load` or `on_load_async` event listener in plugins.
    But those views will be put as an argument for the `on_init` event.

    For some people, they may even have hundreds of tabs opened.
    They may not want a plugin to run on all those views when ST starts up.

### `trim_file_size`

| Type      | Default              |
| --------- | -------------------- |
| `integer` | `20000` (about 20KB) |

Detecting the syntax for the whole file can be resource-consuming if the file is large.
This setting approximately controls how many bytes should be used to represent a file.

### `trim_first_line_length`

| Type      | Default |
| --------- | ------- |
| `integer` | `500`   |

Detecting the syntax for the whole first line can be resource-consuming if it's a super long one-line file.
This setting controls how many characters should be used to represent the first line.

### `trim_suffixes_auto`

| Type      | Default |
| --------- | ------- |
| `boolean` | `false` |

Apart from `trim_suffixes`, also try to remove every sub-extensions when finding a syntax match.
For example, for the file `foo.json.ext1.ext2.ext3`, this setting enables trying the following file names as well.

1. `foo.json.ext1.ext2` (no matching syntax)
1. `foo.json.ext1` (no matching syntax)
1. `foo.json` (matches `JSON` syntax)
1. If there is no `JSON` syntax, then `foo` will be tried.

### `default_syntax_rules`

Syntax rules are the key part of AutoSetSyntax.

!!! example "Structure of syntax rules"

    ```js
    "default_syntax_rules": [
        // syntax rule
        {
            "comment": "...",
            "syntaxes": "...",
            "selector": "...",
            "on_events": null,
            // match rule
            "match": "...",
            "rules": [
                // constraint rule
                {
                    "constraint": "...",
                    "args": ["..."],
                },
                // match rule
                {
                    "match": "...",
                    "rules": [
                        // can be recursive...
                    ],
                },
            ],
        },
        // more syntax rules...
    ],
    ```

    === "Syntax rule"

        A *syntax rule* contains `comment`, `syntaxes`, `selector`, `on_events` and an expanded top-level *match rule*.

        !!! info "Arguments"

            === "comment"

                This is just a optional string which explains what this syntax rule is for.
                It may make your debugging easier.

            === "syntaxes"

                `syntaxes` is a list of [syntax representation][plugin-syntax-representations].
                If there is only one syntax, you can simply un-list it into a string.
                If the top-level `match` is satisfied by `rules`, the first usable syntax in `syntaxes`
                will be assigned to the view.

            === "selector"

                Limit this *syntax rule* only works when the `selector` matches the top scope.
                Learn more about selectors from [ST official docs][st-docs-selectors].

            === "on_events"

                `on_events` is a list of event names or (by default) `null`.
                It's used to restrict this syntax rule only works if this run is triggered by some certain events.
                If it's `null`, then there is no restriction.

                !!! failure

                    If you use an empty list, then this syntax rule will never be evaluated.

                !!! info "Available Events"

                    | Event Name | Meaning |
                    | ---------- | ------- |
                    | `"command"` | This run is triggered by the `auto_set_syntax` command. |
                    | `"init"` | This run is triggered by startup views. |
                    | `"load"` | This run is triggered because a file gets loaded. |
                    | `"modify"` | This run is triggered because of a buffer modification. |
                    | `"new"` | This run is triggered because of a newly created window. |
                    | `"reload"` | This run is triggered because a file has been reloaded. |
                    | `"revert"` | This run is triggered because of the `revert` command. |
                    | `"save"` | This run is triggered because of the buffer gets saved. |
                    | `"untransientize"` | This run is triggered because a transient view becomes a normal view. |

    === "Match rule"

        A *match rule* may recursively contain any amount of *match rule* and *constraint rule*
        so you can build complex rules basing on your needs.

        !!! info "Arguments"

            The default value of the `match` is [`"any"`][plugin-builtin-matches-any],
            which tests whether there is any `rules` satisfied.

        !!! tip

            You may learn more about built-in `match`es [here][plugin-builtin-matches].

    === "Constraint rule"

        A *constraint rule* is the lowest-level rule, which tests an actual constraint.

        !!! tip

            You may learn more about built-in `constraint`s [here][plugin-builtin-constraints].

!!! warning

    It's not recommended to directly override `default_syntax_rules` because that stops you from possible future
    updates for `default_syntax_rules`. The recommended way is putting your syntax rules in `user_syntax_rules`.
    And put project-specific syntax rules in `project_syntax_rules` in [project settings][plugin-project-settings].

### `default_trim_suffixes`

| Type       | Default                                                 |
| ---------- | ------------------------------------------------------- |
| `string[]` | `#!js [ ".dist", ".local", /* many other suffixes */ ]` |

These suffixes are considered unimportant in a file name.
AutoSetSyntax will try to remove them from the file name and maybe a syntax will be found for a trimmed file name.

!!! warning

    It's not recommended to directly override `default_trim_suffixes` because that stops you from possible future
    updates for `default_trim_suffixes`. The recommended way is putting your suffixes in `user_trim_suffixes`.
    And put project-specific suffixes in `project_trim_suffixes` in [project settings][plugin-project-settings].

## Terms and Explanations

### Syntax Representations

When we talk about setting "syntax" in plugin settings, there are three ways you can use.

!!! example

    Let's take the built-in `JavaScript` syntax as an example.

    === "By scope"

        You can use `"scope:TOP_SCOPE"` to represents a syntax.

        For example, the top scope of `JavaScript` is `source.js`.
        Thus, you can use `"scope:source.js"`.

        !!! tip

            To show the scope at the caret position, press ++ctrl+alt+shift+p++.

    === "By name"

        You can use the syntax name to represent a syntax.

        For example, it's `JavaScript` for the `JavaScript` syntax.
        Thus, you can use `"JavaScript"`.

        !!! info

            The syntax name is shown in the bottom-right corner of ST.

        !!! warning

            If you manually type a syntax name, note that it's case-sensitive.

    === "By path"

        You can use a partial path (or a full one if you prefer) of a syntax to represent it.

        For example, the full path for the `JavaScript` syntax is `Packages/JavaScript/JavaScript.sublime-syntax`.
        Theoretically, you may use any substring of the full path to represent it.
        But if your partial path is not unique, it may represent other syntaxes as well and causes unwanted behavior.
        Thus, if you want to go the "by path" way, I recommend using `"/JavaScript/JavaScript."`.

    === "Summary"

        All of followings represent the same syntax, `JavaScript`.

        - Top scope: `"scope:source.js"`
        - Name: `"JavaScript"`
        - Partial path: `"/JavaScript/JavaScript."`
        - Full path: `"Packages/JavaScript/JavaScript.sublime-syntax"`

### Project Settings

To edit project settings, go to `Project` » `Edit Project`.

!!! example

    ```js
    {
        "folders": [
            // ...
        ],
        "settings": {
            "AutoSetSyntax": {
                // use JavaScript as the new file syntax
                "new_file_syntax": "scope:source.js",
                "project_syntax_rules": [
                    // specific rules only for this project
                ],
                "project_trim_suffixes": [
                    // specific trimmed suffixes only for this project
                ],
                // maybe other plugin settings...
            },
        },
    }
    ```

    You can override any plugin setting in project settings. But most likely, you are just interested in
    `new_file_syntax`, `project_syntax_rules` and probably `project_trim_suffixes`.

## Appendix

### Built-in `Match`es

#### `all`

!!! example

    ```js
    {
        "match": "all",
        "rules": [ /* some match rules or constraint rules */ ],
    }
    ```

    Test whether all rules in `rules` are satisfied.

#### `any`

!!! example

    ```js
    {
        "match": "any",
        "rules": [ /* some match rules or constraint rules */ ],
    }
    ```

    Test whether there is any rule in `rules` satisfied.

#### `ratio`

!!! example

    ```js
    {
        "match": "ratio",
        "rules": [ /* some match rules or constraint rules */ ],
        "args": [2, 3],
    }
    ```

    Test whether at least $\frac{2}{3}$ of rules in `rules` are satisfied.

#### `some`

!!! example

    ```js
    {
        "match": "some",
        "rules": [ /* some match rules or constraint rules */ ],
        "args": [4],
    }
    ```

    Test whether at least 4 rules in `rules` are satisfied.

### Built-in `Constraint`s

!!! tip "Tip: Directory Separator"

    For path-related constraints, the directory separator is always `/` no matter what OS you are on.
    This should simplify the rule definitions.

!!! tip "Tip: Inverted Result"

    For all constraint rules, you may set `inverted` to `true` to invert the test result.

    ```js
    {
        // This means testing the file does NOT contains `string_a` or `string_b`.
        "constraint": "contains",
        "args": ["string_a", "string_b"],
        "inverted": true,
    }
    ```

    !!! warning

        Under certain circumstances, the test result will not be inverted.
        For example, if the `is_size` constraint tests a unsaved buffer,
        the result will always be `false` no matter `inverted` is `true` or `false`,
        because a unsaved buffer has no file size.

#### `contains`

!!! example

    ```js
    {
        "constraint": "contains",
        "args": ["string_a", "string_b"],
        "kwargs": { "threshold": 2 },
    }
    ```

    Test whether the file contains string literals `string_a` or `string_b`.
    At least `2` occurrences should be found.

#### `contains_regex`

!!! example

    ```js
    {
        "constraint": "contains_regex",
        "args": ["string_[ab]", "^import\\s"],
        "kwargs": {
            "regex_flags": ["MULTILINE"],
            "threshold": 2,
        },
    }
    ```

    Test whether the file contains regexes `string_[ab]` or `^import\s`.
    At least `2` occurrences should be found.

#### `first_line_contains`

!!! example

    ```js
    {
        "constraint": "first_line_contains",
        "args": ["string_a", "string_b"],
    }
    ```

    Test whether the first line contains string literals `string_a` or `string_b`.

#### `first_line_contains_regex`

!!! example

    ```js
    {
        "constraint": "first_line_contains_regex",
        "args": ["string_[ab]", "^import\\s"],
        "kwargs": { "regex_flags": ["MULTILINE"] },
    }
    ```

    Test whether the first line contains regexes `string_[ab]` or `^import\s`.

#### `relative_exists`

!!! example

    ```js
    {
        "constraint": "relative_exists",
        "args": ["foo", "bar/"],
    }
    ```

    Test whether file `foo` or directory `bar/` exists relatively to the file.

#### `is_arch`

!!! example

    ```js
    {
        "constraint": "is_arch",
        "args": ["x32", "arm64"],
    }
    ```

    Test whether the system arch is `x32` or `arm64`.

    !!! info

        Available platforms are: `x32`, `x64`, and `arm64`.

#### `is_extension`

!!! example

    ```js
    {
        "constraint": "is_extension",
        "args": [".rb", ".rake"],
        "kwargs": {"case_insensitive": false},
    }
    ```

    Test whether the file extension is `.rb` or `.rake`.

    !!! info

        If `case_insensitive` is not provided, it will be `true` on Windows but `false` on other OSes.

#### `is_guesslang_enabled`

!!! example

    ```js
    {
        "constraint": "is_guesslang_enabled",
    }
    ```

    Test whether the `guesslang` server is enabled.

#### `is_in_git_repo`

!!! example

    ```js
    {
        "constraint": "is_in_git_repo",
    }
    ```

    Test whether the file is in a git repository.

#### `is_in_hg_repo`

!!! example

    ```js
    {
        "constraint": "is_in_hg_repo",
    }
    ```

    Test whether the file is in a Mercurial repository.

#### `is_in_python_django_project`

!!! example

    ```js
    {
        "constraint": "is_in_python_django_project",
    }
    ```

    Test whether the file is in a (Python) Django project.

#### `is_in_ruby_on_rails_project`

!!! example

    ```js
    {
        "constraint": "is_in_ruby_on_rails_project",
    }
    ```

    Test whether the file is in a Ruby on Rails project.

#### `is_in_svn_repo`

!!! example

    ```js
    {
        "constraint": "is_in_svn_repo",
    }
    ```

    Test whether the file is in a SVN repository.

#### `is_interpreter`

!!! example

    ```js
    {
        "constraint": "is_interpreter",
        "args": ["bash", "zsh"],
    }
    ```

    Test any of the followings

    - the interpreter in shebang
    - the `syntax` in the VIM's syntax line

    is `bash` or `zsh`.

#### `is_line_count`

!!! example

    ```js
    {
        "constraint": "is_line_count",
        "args": [">", 500],
    }
    ```

    Test whether the file has more than 500 lines.

    !!! info

        Available comparators are: `<`, `<=`, `==`, `>=`, `>` and `!=`.

#### `is_name`

!!! example

    ```js
    {
        "constraint": "is_name",
        "args": ["foo", "bar"],
        "kwargs": {"case_insensitive": false},
    }
    ```

    Test whether the file name is `foo` or `bar`.

    !!! info

        If `case_insensitive` is not provided, it will be `true` on Windows but `false` on other OSes.

#### `is_platform`

!!! example

    ```js
    {
        "constraint": "is_platform",
        "args": ["linux", "windows"],
    }
    ```

    Test whether the system platform is `Linux` or `Windows`.

    !!! info

        Available platforms are: `linux`, `osx`, and `windows`.

#### `is_platform_arch`

!!! example

    ```js
    {
        "constraint": "is_platform_arch",
        "args": ["linux_x64", "windows_x32", "osx_arm64"],
    }
    ```

    Test whether the system platform and arch is `Linux 64-bit`, `Windows 32-bit` or `Apple M1`.

    !!! info

        Available `platform_arch` are combinations of (`linux`, `osx`, `windows`) and (`x32`, `x64`, `arm64`)
        using a `_` as the delimiter.

#### `is_rails_file`

!!! example

    ```js
    {
        "constraint": "is_rails_file",
    }
    ```

    Test whether the file is a `Ruby on Rails` file.

#### `is_size`

!!! example

    ```js
    {
        "constraint": "is_size",
        "args": [">", 5000],
    }
    ```

    Test whether the file size is greater than `5000` bytes (about `5` KB).

    !!! info

        Available comparators are: `<`, `<=`, `==`, `>=`, `>` and `!=`.

#### `name_contains`

!!! example

    ```js
    {
        "constraint": "name_contains",
        "args": ["foo", "bar"],
    }
    ```

    Test whether the file name contains `foo` or `bar`.

#### `name_contains_regex`

!!! example

    ```js
    {
        "constraint": "name_contains_regex",
        "args": ["^foo", "bar$"],
        "kwargs": { "regex_flags": ["MULTILINE"] },
    }
    ```

    Test whether the file name contains regexes `^foo` or `bar$`.

#### `path_contains`

!!! example

    ```js
    {
        "constraint": "path_contains",
        "args": ["foo", "bar"],
    }
    ```

    Test whether the file path contains `foo` or `bar`.

#### `path_contains_regex`

!!! example

    ```js
    {
        "constraint": "path_contains_regex",
        "args": ["/conf/.*\\.conf$", "/assets/.*\\.js$"],
        "kwargs": { "regex_flags": ["MULTILINE"] },
    }
    ```

    Test whether the file path contains regexes `/conf/.*\.conf$` or `/assets/.*\.js$`.

### Regular Expression Flags

Some `constraint`s allow you to use (Python) regexes in `args`.
There are two ways to use regex flags on those regexes.

=== "Inline Regex Flags"

    !!! example

        ```js
        {
            "constraint": "contains_regex",
            "args": ["(?i:foo)_bar"],
        }
        ```

        This will matches `FoO_bar`.

    !!! info

        If you want to learn more, you may read [inline regex flags][python-regex-inline-flags].

=== "`regex_flags` in `kwargs`"

    By default, `#!py ["MULTILINE"]` is used for convenience.

    !!! warning

        Note that those `regex_flags` will be applied to **ALL** regexes.

    !!! example

        ```js
        {
            "constraint": "contains_regex",
            "args": ["string_[ab]", "^import\\s"],
            "kwargs": { "regex_flags": ["IGNORECASE", "MULTILINE"] },
        }
        ```

        This will make `string_[ab]` and `^import\s` matching case-insensitive.

    !!! info "Common Flags"

        | Flag      | Meaning |
        | --------- | ------- |
        | `"IGNORECASE"` | Ignore case (case-insensitive). |
        | `"I"` | An alias of `"IGNORECASE"`. |
        | `"MULTILINE"` | Make `^` matches at line beginnings and `$` matches at line endings. |
        | `"M"` | An alias of `"MULTILINE"`. |
        | `"DOTALL"` | Make `.` matches any character, including a newline. |
        | `"S"` | An alias of `"DOTALL"`. |

        If you want to learn more, you may read Python's docs about the [`re` module][python-regex-flags].
