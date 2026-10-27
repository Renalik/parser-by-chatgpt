"""Portable launcher checks; the packaged Windows smoke test also exercises DPAPI."""

from pathlib import Path
import os
import pytest
from desktop.launcher import InstanceLock, resource_root
from desktop.credentials import save_api_key, load_api_key


def test_single_instance_releases_lock(tmp_path):
    first = InstanceLock(tmp_path)
    second = InstanceLock(tmp_path)
    try:
        assert first.acquire()
        assert not second.acquire()
        first.close()
        assert second.acquire()
    finally:
        first.close()
        second.close()


def test_resource_root_contains_frontend_source():
    assert (resource_root() / "frontend" / "package.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="DPAPI работает только в Windows")
def test_windows_credential_roundtrip(tmp_path):
    save_api_key("test-only-value", tmp_path)
    assert load_api_key(tmp_path) == "test-only-value"
    assert b"test-only-value" not in (tmp_path / "api-key.dpapi").read_bytes()
    save_api_key("", tmp_path)
    assert load_api_key(tmp_path) == ""
