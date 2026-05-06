"""In-memory repositories for v0. A Postgres-backed implementation can replace
these later behind the same interface.
"""

from __future__ import annotations

from threading import RLock

from app.schemas.determination import Determination
from app.schemas.patient import Patient
from app.schemas.policy import Policy


class _Repo[T]:
    def __init__(self) -> None:
        self._items: dict[str, T] = {}
        self._lock = RLock()

    def put(self, key: str, value: T) -> T:
        with self._lock:
            self._items[key] = value
        return value

    def get(self, key: str) -> T | None:
        with self._lock:
            return self._items.get(key)

    def list(self) -> list[T]:
        with self._lock:
            return list(self._items.values())

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._items.pop(key, None) is not None


policy_repo: _Repo[Policy] = _Repo()
patient_repo: _Repo[Patient] = _Repo()
determination_repo: _Repo[Determination] = _Repo()
