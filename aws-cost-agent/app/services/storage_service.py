"""Storage service scaffold.

Replace with S3/local persistence as needed.
"""

from __future__ import annotations

from typing import Any, Dict


class StorageService:
    def __init__(self):
        self.use_s3 = False
        self._config: Dict[str, Any] = {}

    async def initialize(self) -> None:
        # TODO: initialize S3 client / load config
        self._config = {}

    async def cleanup(self) -> None:
        return

    def get_config(self) -> Dict[str, Any]:
        return self._config


storage = StorageService()
