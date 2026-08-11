"""Storage abstraction: local filesystem for the POC.

Swap `LocalStorage` for an `S3Storage` implementing the same three methods
(`save`, `read`, `abspath`) to move to hosted/S3-compatible storage without
touching any caller. Layout is deliberately Client > Fund > Period so the
whole history for a fund/period can be located, archived, or regenerated
without re-uploading anything.
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\-.]+", "_", value.strip())
    return value.strip("_") or "unnamed"


class StorageBackend(ABC):
    @abstractmethod
    def save(self, relative_path: str, content: bytes) -> str:
        """Persist bytes at relative_path, return the stored relative path."""

    @abstractmethod
    def read(self, relative_path: str) -> bytes:
        ...

    @abstractmethod
    def abspath(self, relative_path: str) -> Path:
        ...


class LocalStorage(StorageBackend):
    def __init__(self, root: Path | None = None):
        self.root = root or settings.storage_root

    def abspath(self, relative_path: str) -> Path:
        return self.root / relative_path

    def save(self, relative_path: str, content: bytes) -> str:
        path = self.abspath(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return relative_path

    def read(self, relative_path: str) -> bytes:
        return self.abspath(relative_path).read_bytes()


storage = LocalStorage()


def client_dir(client_id: int) -> str:
    return f"clients/{client_id}"


def fund_dir(client_id: int, fund_id: int) -> str:
    return f"{client_dir(client_id)}/funds/{fund_id}"


def period_dir(client_id: int, fund_id: int, period_id: int) -> str:
    return f"{fund_dir(client_id, fund_id)}/periods/{period_id}"


def workbook_path(client_id: int, fund_id: int, period_id: int, filename: str) -> str:
    return f"{period_dir(client_id, fund_id, period_id)}/workbooks/{slugify(filename)}"


def template_path(client_id: int, fund_id: int, filename: str, version: int) -> str:
    return f"{fund_dir(client_id, fund_id)}/templates/v{version}_{slugify(filename)}"


def draft_path(client_id: int, fund_id: int, period_id: int, filename: str) -> str:
    return f"{period_dir(client_id, fund_id, period_id)}/drafts/{slugify(filename)}"


def final_path(client_id: int, fund_id: int, period_id: int, filename: str) -> str:
    return f"{period_dir(client_id, fund_id, period_id)}/final/{slugify(filename)}"


def mapping_config_path(client_id: int, fund_id: int, version: int) -> str:
    return f"{fund_dir(client_id, fund_id)}/mapping_configs/v{version}.json"
