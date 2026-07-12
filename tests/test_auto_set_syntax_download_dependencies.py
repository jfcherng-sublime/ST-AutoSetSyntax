"""Tests for the dependency-download command's control flow (success/failure signaling, checksum handling)."""

import urllib.error

import pytest


def _import_module():
    import plugin.commands.auto_set_syntax_download_dependencies as mod

    return mod


@pytest.fixture(autouse=True)
def _stub_dialogs(monkeypatch):
    """`sublime.error_message`/`message_dialog` don't exist on the test stub; make them no-ops by default."""
    mod = _import_module()
    monkeypatch.setattr(mod.sublime, "error_message", lambda msg: None, raising=False)
    monkeypatch.setattr(mod.sublime, "message_dialog", lambda msg: None, raising=False)


class TestPrepareDependencies:
    def test_download_failure_returns_false_without_extracting(self, monkeypatch):
        mod = _import_module()

        def _boom(url, **kwargs):
            raise OSError("network down")

        monkeypatch.setattr(mod, "simple_urlopen", _boom)
        extract_calls = []
        monkeypatch.setattr(mod, "decompress_buffer", lambda *a, **kw: extract_calls.append(1) or True)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is False
        assert extract_calls == []

    def test_checksum_mismatch_returns_false_without_extracting(self, monkeypatch):
        mod = _import_module()

        def _urlopen(url, **kwargs):
            if url.endswith(".sha256"):
                return b"0" * 64
            return b"archive-bytes"

        monkeypatch.setattr(mod, "simple_urlopen", _urlopen)
        extract_calls = []
        monkeypatch.setattr(mod, "decompress_buffer", lambda *a, **kw: extract_calls.append(1) or True)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is False
        assert extract_calls == []

    def test_checksum_sidecar_missing_404_skips_validation_and_proceeds(self, monkeypatch, tmp_path):
        mod = _import_module()
        libs_dir = tmp_path / "libs"

        def _urlopen(url, **kwargs):
            if url.endswith(".sha256"):
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            return b"archive-bytes"

        extract_calls = []

        def _fake_extract(buffer, *, filename, dst_dir):
            extract_calls.append(1)
            (dst_dir / libs_dir.name).mkdir(parents=True)
            return True

        monkeypatch.setattr(mod, "simple_urlopen", _urlopen)
        monkeypatch.setattr(mod, "decompress_buffer", _fake_extract)
        monkeypatch.setattr(mod, "PLUGIN_PY_LIBS_DIR", libs_dir)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is True
        assert extract_calls == [1]

    def test_checksum_sidecar_network_error_aborts_without_extracting(self, monkeypatch):
        """A transient failure fetching the sidecar must NOT be treated the same as "no checksum published"."""
        mod = _import_module()

        def _urlopen(url, **kwargs):
            if url.endswith(".sha256"):
                raise OSError("network down")
            return b"archive-bytes"

        monkeypatch.setattr(mod, "simple_urlopen", _urlopen)
        extract_calls = []
        monkeypatch.setattr(mod, "decompress_buffer", lambda *a, **kw: extract_calls.append(1) or True)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is False
        assert extract_calls == []

    def test_extraction_failure_leaves_old_deps_intact(self, monkeypatch, tmp_path):
        mod = _import_module()

        libs_dir = tmp_path / "libs"
        libs_dir.mkdir()
        (libs_dir / "sentinel.txt").write_text("old deps")

        def _urlopen(url, **kwargs):
            if url.endswith(".sha256"):
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            return b"archive-bytes"

        def _boom_extract(*a, **kw):
            raise OSError("corrupt archive")

        monkeypatch.setattr(mod, "simple_urlopen", _urlopen)
        monkeypatch.setattr(mod, "decompress_buffer", _boom_extract)
        monkeypatch.setattr(mod, "PLUGIN_PY_LIBS_DIR", libs_dir)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is False
        assert (libs_dir / "sentinel.txt").exists()  # old deps must survive a failed extraction

    def test_successful_prepare_replaces_deps_dir(self, monkeypatch, tmp_path):
        mod = _import_module()

        libs_dir = tmp_path / "libs"
        libs_dir.mkdir()
        (libs_dir / "sentinel.txt").write_text("old deps")

        def _urlopen(url, **kwargs):
            if url.endswith(".sha256"):
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            return b"archive-bytes"

        def _fake_extract(buffer, *, filename, dst_dir):
            # archives extract into a `dst_dir / <libs-dir-name>` subfolder, like the real tarball does
            extracted = dst_dir / libs_dir.name
            extracted.mkdir(parents=True)
            (extracted / "new_marker.txt").write_text("new deps")
            return True

        monkeypatch.setattr(mod, "simple_urlopen", _urlopen)
        monkeypatch.setattr(mod, "decompress_buffer", _fake_extract)
        monkeypatch.setattr(mod, "PLUGIN_PY_LIBS_DIR", libs_dir)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is True
        assert not (libs_dir / "sentinel.txt").exists()
        assert (libs_dir / "new_marker.txt").exists()

    def test_extracted_archive_missing_expected_subdir_returns_false(self, monkeypatch, tmp_path):
        """The archive succeeded but didn't contain the expected top-level directory -> treat as failure."""
        mod = _import_module()

        libs_dir = tmp_path / "libs"
        libs_dir.mkdir()
        (libs_dir / "sentinel.txt").write_text("old deps")

        def _urlopen(url, **kwargs):
            if url.endswith(".sha256"):
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            return b"archive-bytes"

        monkeypatch.setattr(mod, "simple_urlopen", _urlopen)
        monkeypatch.setattr(mod, "decompress_buffer", lambda *a, **kw: True)  # extracts nothing useful
        monkeypatch.setattr(mod, "PLUGIN_PY_LIBS_DIR", libs_dir)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is False
        assert (libs_dir / "sentinel.txt").exists()


class TestSimpleUrlopen:
    def test_passes_a_timeout_to_urlopen(self, monkeypatch):
        """A hung/black-holed connection must not block the download thread forever -- urlopen()
        has no timeout by default, so one must be passed explicitly."""
        mod = _import_module()

        calls = []

        class _FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, n=-1):
                return b""

            def info(self):
                return {}

        def _fake_urlopen(url, **kwargs):
            calls.append(kwargs)
            return _FakeResponse()

        monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen)

        mod.simple_urlopen("https://example.invalid/whatever")

        assert calls and calls[0].get("timeout") is not None


class TestWorker:
    def test_worker_does_not_show_success_dialog_after_failure(self, monkeypatch):
        mod = _import_module()

        dialogs = []
        monkeypatch.setattr(mod.sublime, "message_dialog", lambda msg: dialogs.append(("message", msg)), raising=False)
        monkeypatch.setattr(mod.sublime, "error_message", lambda msg: dialogs.append(("error", msg)), raising=False)
        monkeypatch.setattr(
            mod.AutoSetSyntaxDownloadDependenciesCommand, "_prepare_dependencies", classmethod(lambda cls: False)
        )

        mod.AutoSetSyntaxDownloadDependenciesCommand._worker()

        assert not any(kind == "message" and "Finish" in msg for kind, msg in dialogs)

    def test_worker_shows_success_dialog_after_success(self, monkeypatch, tmp_path):
        mod = _import_module()

        magika_dir = tmp_path / "magika"
        magika_dir.mkdir()
        monkeypatch.setattr(mod, "PLUGIN_PY_LIBS_DIR", tmp_path)

        dialogs = []
        monkeypatch.setattr(mod.sublime, "message_dialog", lambda msg: dialogs.append(("message", msg)), raising=False)
        monkeypatch.setattr(mod.sublime, "error_message", lambda msg: dialogs.append(("error", msg)), raising=False)
        monkeypatch.setattr(
            mod.AutoSetSyntaxDownloadDependenciesCommand, "_prepare_dependencies", classmethod(lambda cls: True)
        )

        mod.AutoSetSyntaxDownloadDependenciesCommand._worker()

        assert any(kind == "message" and "Finish" in msg for kind, msg in dialogs)
        assert not any(kind == "error" for kind, msg in dialogs)
