"""Smoke test — verifies the package imports and exposes its version."""

import lastra_convert


def test_version_present() -> None:
    assert isinstance(lastra_convert.__version__, str)
    assert lastra_convert.__version__.count(".") >= 1
