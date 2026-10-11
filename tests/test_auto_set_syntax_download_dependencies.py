"""Tests for the dependency-download command's control flow (success/failure signaling, checksum handling)."""

import hashlib
import urllib.error

import pytest

_ARCHIVE = b"archive-bytes"
_VALID_CHECKSUM = hashlib.sha256(_ARCHIVE).hexdigest().encode()


def _import_module():
    import plugin.commands.auto_set_syntax_download_dependencies as mod

    return mod


def _serve(checksum: bytes | Exception = _VALID_CHECKSUM, requested: list[str] | None = None):
    """A fake `simple_urlopen` serving `_ARCHIVE` and, for its `.sha256` sidecar, `checksum` (or raising it)."""

    def _urlopen(url, **kwargs):
        if requested is not None:
            requested.append(url)
        if not url.endswith(".sha256"):
            return _ARCHIVE
        if isinstance(checksum, Exception):
            raise checksum
        return checksum

    return _urlopen


def _not_found(url: str = "https://example.invalid/x.sha256") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, 404, "Not Found", None, None)  # type: ignore[arg-type]


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

        monkeypatch.setattr(mod, "simple_urlopen", _serve(b"0" * 64))
        extract_calls = []
        monkeypatch.setattr(mod, "decompress_buffer", lambda *a, **kw: extract_calls.append(1) or True)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is False
        assert extract_calls == []

    @pytest.mark.parametrize(
        "checksum",
        [_not_found(), OSError("network down"), b"", b"  \n"],
        ids=["404", "network-error", "empty", "blank"],
    )
    def test_unverifiable_archive_is_never_downloaded_or_installed(self, monkeypatch, checksum):
        """No usable checksum means nothing to verify against: a missing (404) or empty sidecar used
        to skip validation and install whatever was downloaded. Fetched first, so a sidecar that
        can't be had doesn't cost the (large) archive download either."""
        mod = _import_module()

        requested: list[str] = []
        monkeypatch.setattr(mod, "simple_urlopen", _serve(checksum, requested))
        extract_calls = []
        monkeypatch.setattr(mod, "decompress_buffer", lambda *a, **kw: extract_calls.append(1) or True)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is False
        assert extract_calls == []
        assert all(url.endswith(".sha256") for url in requested)

    def test_checksum_comparison_ignores_case_and_surrounding_whitespace(self, monkeypatch, tmp_path):
        mod = _import_module()
        libs_dir = tmp_path / "libs"

        def _fake_extract(buffer, *, filename, dst_dir):
            (dst_dir / libs_dir.name).mkdir(parents=True)
            return True

        monkeypatch.setattr(mod, "simple_urlopen", _serve(_VALID_CHECKSUM.upper() + b"\n"))
        monkeypatch.setattr(mod, "decompress_buffer", _fake_extract)
        monkeypatch.setattr(mod, "PLUGIN_PY_LIBS_DIR", libs_dir)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is True

    def test_extraction_failure_leaves_old_deps_intact(self, monkeypatch, tmp_path):
        mod = _import_module()

        libs_dir = tmp_path / "libs"
        libs_dir.mkdir()
        (libs_dir / "sentinel.txt").write_text("old deps")

        def _boom_extract(*a, **kw):
            raise OSError("corrupt archive")

        monkeypatch.setattr(mod, "simple_urlopen", _serve())
        monkeypatch.setattr(mod, "decompress_buffer", _boom_extract)
        monkeypatch.setattr(mod, "PLUGIN_PY_LIBS_DIR", libs_dir)

        assert mod.AutoSetSyntaxDownloadDependenciesCommand._prepare_dependencies() is False
        assert (libs_dir / "sentinel.txt").exists()  # old deps must survive a failed extraction

    def test_successful_prepare_replaces_deps_dir(self, monkeypatch, tmp_path):
        mod = _import_module()

        libs_dir = tmp_path / "libs"
        libs_dir.mkdir()
        (libs_dir / "sentinel.txt").write_text("old deps")

        def _fake_extract(buffer, *, filename, dst_dir):
            # archives extract into a `dst_dir / <libs-dir-name>` subfolder, like the real tarball does
            extracted = dst_dir / libs_dir.name
            extracted.mkdir(parents=True)
            (extracted / "new_marker.txt").write_text("new deps")
            return True

        monkeypatch.setattr(mod, "simple_urlopen", _serve())
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

        monkeypatch.setattr(mod, "simple_urlopen", _serve())
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
