"""Base types for platform adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class JobPosting:
    title: str
    url: str
    platform: str


class PlatformError(RuntimeError):
    """Raised when an adapter fails to fetch jobs for any reason."""


class PlatformAdapter(ABC):
    def __init__(self, name: str, public_url: str) -> None:
        self.name = name
        self.public_url = public_url

    @abstractmethod
    async def fetch(self) -> list[JobPosting]:
        """Return every currently-visible job posting on the platform."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r})"
