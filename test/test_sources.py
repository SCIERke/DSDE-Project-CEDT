from datetime import date

from ingest import sources
from ingest.downloader import DataDownloader


def registered(month, monkeypatch, identity=None):
    monkeypatch.setattr(sources, "TRAFFY_IDENTITY", identity or {})
    d = DataDownloader()
    sources.register_sources(d, month)
    return d.sources


def test_month_drives_traffy_name(monkeypatch):
    s = registered("2024-02", monkeypatch, {"name": "n", "org": "o", "email": "e", "purpose": "p"})
    assert s["traffy:2024-02"].params["file_name"] == "bangkok_2024-02"
    assert "overpass:cam915" in s  # not month-dependent


def test_traffy_skipped_without_identity(monkeypatch):
    assert not [n for n in registered("2025-06", monkeypatch) if n.startswith("traffy")]


def test_last_full_month(monkeypatch):
    class D(date):
        @classmethod
        def today(cls): return cls(2026, 1, 15)
    monkeypatch.setattr(sources, "date", D)
    assert sources.last_full_month() == "2025-12"
