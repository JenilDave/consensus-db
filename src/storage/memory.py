from typing import Optional
from src.storage.base import BaseStorage
import threading

class MemoryStorage(BaseStorage):
    """
    In-memory implementation of the Key-Value storage engine.
    Uses a standard Python dictionary and a lock for thread-safety.
    """
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def put(self, key: str, value: str) -> bool:
        with self._lock:
            self._store[key] = value
            return True

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            return self._store.get(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False
