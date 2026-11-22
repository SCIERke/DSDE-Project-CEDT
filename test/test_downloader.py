import requests

from ingest.downloader import DataDownloader


class Resp:
    def __init__(self, ctype, text, js=None):
        self.headers, self.text, self._js = {"content-type": ctype}, text, js

    def raise_for_status(self): ...
    def json(self): return self._js


def test_json_and_text_fallback(monkeypatch):
    replies = {"j": Resp("application/json", "", {"a": 1}), "t": Resp("text/csv", "a,b\n1,2")}
    monkeypatch.setattr(requests, "request", lambda method, url, **kw: replies[url])
    d = DataDownloader()
    d.register("j", "j")
    d.register("t", "t")
    assert d.download_all() == {"j": {"a": 1}, "t": "a,b\n1,2"}
