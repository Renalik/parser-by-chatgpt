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


def test_monochrome_tray_icon():
    from desktop.tray import icon_pixels

    pixels, mask = icon_pixels()
    assert len(pixels) == 32 * 32 * 4 and len(mask) == 32 * 4
    opaque = [
        tuple(pixels[i : i + 4]) for i in range(0, len(pixels), 4) if pixels[i + 3]
    ]
    assert set(opaque) == {(0, 0, 0, 255), (255, 255, 255, 255)}


@pytest.mark.skipif(os.name != "nt", reason="Native Windows notification window")
def test_native_tray_lifecycle():
    from desktop.tray import TrayIcon

    tray = TrayIcon(lambda action: None)
    try:
        tray.start()
        assert tray.window_created
    finally:
        tray.stop()
    assert not tray.thread.is_alive()
