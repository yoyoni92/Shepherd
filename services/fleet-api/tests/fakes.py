"""Fake Google Drive client so tests never touch the network.

``fake_build_service`` returns a replacement for ``drive._build_service``; monkeypatch
it onto the drive module. Set ``get_exc`` to simulate an inaccessible folder (validation
failure) and ``build_exc`` to simulate a bad credentials blob.
"""
from __future__ import annotations


class _Exec:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc

    def execute(self):
        if self._exc is not None:
            raise self._exc
        return self._result


class _Files:
    def __init__(self, get_exc=None):
        self._get_exc = get_exc

    def get(self, **_kw):
        return _Exec(result={"id": "f", "name": "folder"}, exc=self._get_exc)

    def create(self, **_kw):
        return _Exec(result={"id": "file-1", "webViewLink": "https://drive/file/view"})


class _Permissions:
    def create(self, **_kw):
        return _Exec(result={})


class FakeService:
    def __init__(self, get_exc=None):
        self._files = _Files(get_exc)
        self._permissions = _Permissions()

    def files(self):
        return self._files

    def permissions(self):
        return self._permissions


def fake_build_service(*, get_exc=None, build_exc=None):
    """Return a stand-in for ``drive._build_service``."""

    def _build(credentials_json: str):
        if build_exc is not None:
            raise build_exc
        return FakeService(get_exc=get_exc)

    return _build
