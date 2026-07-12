"""Tests for the paste/modify-detection heuristic in plugin/listener.py.

`_try_assign_syntax_when_text_changed` decides, from the shape of a text edit alone, whether
it's worth re-running syntax detection: a paste (large insert), an edit near the start/end of a
short-enough buffer, or an edit deep in the middle of a large file (skipped -- unlikely to reveal
anything about the file's type). This had zero dedicated test coverage.
"""

from unittest.mock import MagicMock

import plugin.listener as listener_mod


class _FakePos:
    def __init__(self, pt: int, row: int) -> None:
        self.pt = pt
        self.row = row


class _FakeChange:
    def __init__(self, s: str, *, b_pt: int = 0, b_row: int = 0) -> None:
        self.str = s
        self.a = _FakePos(b_pt, b_row)
        self.b = _FakePos(b_pt, b_row)


def _make_view(*, size: int, sel_count: int = 1) -> MagicMock:
    view = MagicMock()
    view.sel.return_value = [MagicMock()] * sel_count
    view.size.return_value = size
    return view


class TestTryAssignSyntaxWhenTextChanged:
    def test_multiple_selections_skipped(self, monkeypatch):
        """Multi-cursor edits are too ambiguous for this heuristic."""
        calls = []
        monkeypatch.setattr(listener_mod, "run_auto_set_syntax_on_view", lambda *a, **kw: calls.append(1) or True)

        view = _make_view(size=100, sel_count=2)
        changes = [_FakeChange("x", b_pt=50, b_row=5)]

        assert listener_mod._try_assign_syntax_when_text_changed(view, changes) is False
        assert calls == []

    def test_large_insert_is_treated_as_paste(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            listener_mod, "run_auto_set_syntax_on_view", lambda v, event, **kw: calls.append((event, kw)) or True
        )

        view = _make_view(size=1000)
        changes = [_FakeChange("x" * 20, b_pt=500, b_row=10)]  # deep in the middle, but large

        assert listener_mod._try_assign_syntax_when_text_changed(view, changes) is True
        assert calls[0][0] == listener_mod.ListenerEvent.PASTE
        assert calls[0][1] == {"must_plaintext": True}

    def test_paste_threshold_is_summed_across_all_changes(self, monkeypatch):
        """Regression-style check: multiple small changes in one batch (e.g. auto-indent
        inserting several separate edits) must have their sizes summed, not just the first one's,
        to decide whether the whole batch looks like a paste."""
        calls = []
        monkeypatch.setattr(
            listener_mod, "run_auto_set_syntax_on_view", lambda v, event, **kw: calls.append(event) or True
        )

        view = _make_view(size=1000)
        changes = [_FakeChange("x" * 3, b_pt=500, b_row=10) for _ in range(3)]  # 3+3+3=9 >= threshold(8)

        assert listener_mod._try_assign_syntax_when_text_changed(view, changes) is True
        assert calls[0] == listener_mod.ListenerEvent.PASTE

    def test_small_edit_in_short_buffer_triggers_modify(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            listener_mod, "run_auto_set_syntax_on_view", lambda v, event, **kw: calls.append((event, kw)) or True
        )

        view = _make_view(size=100)  # under the short-content threshold (300)
        changes = [_FakeChange("x", b_pt=50, b_row=3)]  # not near start or end

        assert listener_mod._try_assign_syntax_when_text_changed(view, changes) is True
        assert calls[0] == (listener_mod.ListenerEvent.MODIFY, {"must_plaintext": True})

    def test_small_edit_on_first_line_of_large_buffer_triggers_modify(self, monkeypatch):
        calls = []
        monkeypatch.setattr(listener_mod, "run_auto_set_syntax_on_view", lambda v, event, **kw: calls.append(event))

        view = _make_view(size=10000)
        changes = [_FakeChange("x", b_pt=5, b_row=0)]  # row 0 = first line

        listener_mod._try_assign_syntax_when_text_changed(view, changes)
        assert calls == [listener_mod.ListenerEvent.MODIFY]

    def test_small_edit_near_end_of_large_buffer_triggers_modify(self, monkeypatch):
        calls = []
        monkeypatch.setattr(listener_mod, "run_auto_set_syntax_on_view", lambda v, event, **kw: calls.append(event))

        view = _make_view(size=10000)
        changes = [_FakeChange("x", b_pt=9999, b_row=50)]  # within _EDIT_END_PROXIMITY(2) of size

        listener_mod._try_assign_syntax_when_text_changed(view, changes)
        assert calls == [listener_mod.ListenerEvent.MODIFY]

    def test_small_edit_deep_in_middle_of_large_buffer_is_skipped(self, monkeypatch):
        calls = []
        monkeypatch.setattr(listener_mod, "run_auto_set_syntax_on_view", lambda *a, **kw: calls.append(1) or True)

        view = _make_view(size=10000)
        changes = [_FakeChange("x", b_pt=5000, b_row=250)]  # not first line, not short, not near end

        assert listener_mod._try_assign_syntax_when_text_changed(view, changes) is False
        assert calls == []
