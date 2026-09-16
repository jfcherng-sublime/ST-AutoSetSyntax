# Detector signatures are deliberately not uniform

Most detectors take a `ViewSnapshot`, but the exec-output detector takes a raw `sublime.View` and
the exec-output and new-file detectors are called directly from `run_auto_set_syntax_on_view()`
rather than from the `_detect()` chain. This is deliberate: building a `ViewSnapshot` reads the
view's content and issues a `stat()` call, and the `EXEC` event fires on every build-panel update,
where none of that snapshot is needed. We chose the per-event cost saving over a uniform detector
signature.

## Considered options

A uniform `(ViewSnapshot, ListenerEvent, MergedSettingsDict) -> SyntaxDecision | None` signature for
all detectors, with exec output taking a snapshot it ignores — rejected for the cost above. A
context object that builds the snapshot lazily would give both, but it is a larger change than the
asymmetry costs, and would push snapshot-construction timing out of the one function that currently
makes it obvious.

## Consequences

The asymmetry reads like an oversight. It isn't — don't "fix" it without measuring what snapshot
construction costs on a busy build panel first.
