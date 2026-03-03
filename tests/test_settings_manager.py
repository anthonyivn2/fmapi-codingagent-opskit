"""Tests for SettingsManager."""

from __future__ import annotations

import json

from fmapi_opskit.settings.manager import SettingsManager


def test_settings_lifecycle(tmp_path):
    p = tmp_path / "deep" / "settings.json"
    mgr = SettingsManager(p)

    # missing → empty
    assert mgr.read() == {}

    # write + read roundtrip
    mgr.write({"env": {"A": "1"}})
    assert mgr.read() == {"env": {"A": "1"}}

    # merge_env adds keys and removes legacy
    p2 = tmp_path / "s2.json"
    p2.write_text(json.dumps({"env": {"KEEP": "v", "OLD": "x"}}))
    mgr2 = SettingsManager(p2)
    mgr2.merge_env({"NEW": "n"}, api_key_helper="/h.sh", legacy_cleanup_keys=("OLD",))
    s = mgr2.read()
    assert s["env"]["NEW"] == "n" and "OLD" not in s["env"]
    assert s["apiKeyHelper"] == "/h.sh"

    # remove_fmapi_keys: full removal deletes file
    p3 = tmp_path / "s3.json"
    p3.write_text(json.dumps({"env": {"ONLY": "m"}, "apiKeyHelper": "/h"}))
    assert SettingsManager(p3).remove_fmapi_keys(("ONLY",)) is True
    assert not p3.is_file()
