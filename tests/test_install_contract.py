"""Offline checks of the bridge/exporter install contract: state-file ownership and the documented install order.

No real accounts, chown or services: os.chown is replaced by a recorder and every path is under tmp_path.
"""

from __future__ import annotations

import os
import runpy
import stat
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE = REPO_ROOT / "deploy" / "scripts" / "cake-autorate-state-bridge"
ENV_EXAMPLE = REPO_ROOT / "deploy" / "scripts" / "bridge.env.example"
EXPORTER_UNIT = REPO_ROOT / "deploy" / "systemd" / "cake-metrics-exporter.service"
README = REPO_ROOT / "README.md"


def _env_keys(text: str) -> dict[str, str]:
    keys = {}
    for line in text.splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            keys[key] = value
    return keys


def test_env_example_sets_state_owner_explicitly() -> None:
    keys = _env_keys(ENV_EXAMPLE.read_text(encoding="utf-8"))
    assert keys["WANCTL_STATE_UID"] == "<exporter-uid>"
    assert keys["WANCTL_STATE_GID"] == "<exporter-gid>"
    assert keys["WANCTL_STATE_CHOWN"] == "1"


def test_state_file_is_private_and_chowned_to_configured_ids_before_replace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "state" / "wan1_state.json"
    monkeypatch.setenv("WANCTL_EXTERNAL_WAN_NAME", "wan1")
    monkeypatch.setenv("WANCTL_EXTERNAL_STATE_PATH", str(state_path))
    monkeypatch.setenv("WANCTL_EXTERNAL_METRICS_DB", str(tmp_path / "metrics-wan1.db"))
    monkeypatch.setenv("WANCTL_EXTERNAL_RTT_ENABLED", "0")
    monkeypatch.setenv("WANCTL_STATE_UID", "4242")
    monkeypatch.setenv("WANCTL_STATE_GID", "4343")
    monkeypatch.setenv("WANCTL_STATE_CHOWN", "1")
    namespace: dict[str, Any] = runpy.run_path(str(BRIDGE))

    events: list[tuple[str, Any]] = []
    real_replace = os.replace

    def fake_chown(path: str, uid: int, gid: int) -> None:
        events.append(("chown", (Path(path).parent, uid, gid, stat.S_IMODE(os.stat(path).st_mode))))

    def tracking_replace(src: str, dst: Any) -> None:
        events.append(("replace", Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(namespace["os"], "chown", fake_chown)
    monkeypatch.setattr(namespace["os"], "replace", tracking_replace)
    namespace["write_state"]({"wan_name": "wan1"})

    assert events[0] == ("chown", (state_path.parent, 4242, 4343, 0o600))
    assert events[1] == ("replace", state_path)
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600


def test_readme_prepares_exporter_account_before_any_unit_starts() -> None:
    readme = README.read_text(encoding="utf-8")
    account_step = readme.index("### Account and directories (before starting any unit)")
    first_start = readme.index("systemctl enable --now cake-autorate-state-bridge@")
    assert account_step < first_start
    assert "WANCTL_STATE_UID" in readme[account_step:first_start]
    assert "User=wanctl" in EXPORTER_UNIT.read_text(encoding="utf-8")
