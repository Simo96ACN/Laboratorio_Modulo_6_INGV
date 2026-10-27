from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LabError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def as_dict(self) -> dict[str, str]:
        return {"status": "ERROR", "code": self.code, "message": self.message}
