# AutoSetSyntax

A Sublime Text 4 plugin that decides which syntax a view should have and assigns it. The domain is
*detection* — turning a view's name, content and surroundings into a syntax choice — not text editing.

## Language

### Detection

**Detector**:
Something that inspects a view snapshot and either reaches a syntax decision or declines. Detectors
are tried in a fixed order; the first one to decide wins.
_Avoid_: strategy, checker, handler, step

**Syntax Decision**:
A detector's verdict that a particular syntax should be assigned, together with the reason it was
reached. A detector that declines produces no syntax decision at all.
_Avoid_: result, match, outcome, choice

**View Snapshot**:
A frozen record of everything detectors are allowed to know about a view — its content, name, path,
encoding, current syntax and caret position — captured at one moment. Detectors never read the live
view.
_Avoid_: context, state, view data

**Listener Event**:
The reason detection is running: a file was opened, saved, reverted, typed into, pasted into, and so
on. Some detectors only apply to some events.
_Avoid_: trigger, hook, action

**Magika**:
Google's deep-learning content-type detector, an optional dependency. It is one detector among
several, consulted only for plain-text views without a useful extension.

### Rules

**Syntax Rule**:
A user-authored entry that names target syntaxes and the conditions under which they apply. Rules are
tried top to bottom; the first to pass wins.
_Avoid_: pattern, mapping, definition

**Syntax Rule Collection**:
The ordered set of syntax rules compiled for one window.

**Constraint**:
A leaf condition on a view snapshot that answers yes or no — "is this extension", "does the first
line contain", "is this inside a Go project".
_Avoid_: check, predicate, test, condition

**Match**:
A combinator over constraints and nested matches — `any`, `all`, `some`, `ratio`. A match decides how
many of its children must pass.
_Avoid_: group, operator, combinator

**Dropped Rule**:
A syntax rule, match or constraint discarded while compiling because its outcome can no longer depend
on the view — it would always pass, or always fail. Dropped rules are reported to the user rather
than silently removed, each carrying the reason it could be dropped in the words of the rule that
settled it — "no extension was given", not just the verdict "never matches".
_Avoid_: pruned rule, optimized-away rule, dead rule

### Configuration

**Merged Settings**:
One window's effective configuration, formed by layering project settings over user settings over
the plugin defaults, plus values derived from those layers.
_Avoid_: config, preferences, options

**Custom Implementation**:
A user-supplied constraint or match, loaded from the user's own package directory at startup and
usable in syntax rules by name like any built-in one.
_Avoid_: plugin, extension, addon
