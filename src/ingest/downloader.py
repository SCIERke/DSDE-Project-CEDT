from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass
class SourceConfig:
    name: str
    url: str
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    method: str = "GET"
    timeout: int = 30


class DataDownloader:
    def __init__(self):
      self.sources: dict[str, SourceConfig] = {}

    def register(self, name: str, url: str, params: dict[str, Any] | None = None, **kwargs) -> SourceConfig:
      self.sources[name] = SourceConfig(name, url, params or {}, **kwargs)
      return self.sources[name]

    def download(self, name: str) -> Any:
      s = self.sources[name]
      r = requests.request(s.method, s.url, params=s.params, headers=s.headers, timeout=s.timeout)
      r.raise_for_status()
      if "json" in r.headers.get("content-type", ""):
        return r.json()
      r.encoding = "utf-8-sig"  # text/csv arrives without a charset; requests would guess latin-1 and mangle Thai
      return r.text

    def download_all(self) -> dict[str, Any]:
      return {name: self.download(name) for name in self.sources}
