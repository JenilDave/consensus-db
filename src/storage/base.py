from abc import ABC, abstractmethod
from typing import Optional

class BaseStorage(ABC):
    """
    Abstract base class for Key-Value storage engine.
    This abstraction allows us to plug in different storage engines
    (e.g., in-memory, disk-based, distributed) in the future.
    """

    @abstractmethod
    def put(self, key: str, value: str) -> bool:
        """Store the value for the given key."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Retrieve the value for the given key. Returns None if not found."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete the value for the given key. Returns True if deleted, False if not found."""
        pass
