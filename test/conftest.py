import pytest

from core import config


@pytest.fixture(autouse=True)
def temp_lake(tmp_path, monkeypatch):
    """Every test gets its own empty DuckLake, so tests never touch data/."""
    monkeypatch.setattr(config, "LAKE_META", str(tmp_path / "lake.ducklake"))
    monkeypatch.setattr(config, "LAKE_DATA", str(tmp_path / "lake") + "/")
