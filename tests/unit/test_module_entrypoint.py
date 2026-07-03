from __future__ import annotations

import runpy

from openinfra.interfaces.cli import OpenInfraCLI


def test_module_entrypoint_invokes_cli(monkeypatch) -> None:
    calls: list[str] = []

    def fake_main() -> int:
        calls.append("called")
        return 0

    monkeypatch.setattr(OpenInfraCLI, "main", staticmethod(fake_main))
    runpy.run_module("openinfra.__main__")

    assert calls == ["called"]
