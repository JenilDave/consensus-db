import json
import os
import threading
from typing import Optional
from src.storage.base import BaseStorage

class DurableStorage(BaseStorage):
    def __init__(self, port: int):
        self.filename = f"data_{port}.jsonl"
        self._store = {}
        self._lock = threading.Lock()
        self.term_id = 1
        self.commit_id = 0
        self._load_from_log()

    def _load_from_log(self):
        if not os.path.exists(self.filename):
            return
        with open(self.filename, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line.strip())
                    op = entry.get("op")
                    key = entry.get("key")
                    val = entry.get("value")
                    cid = entry.get("commit_id", 0)
                    tid = entry.get("term_id", 1)
                    
                    if op == "put":
                        self._store[key] = val
                    elif op == "delete":
                        self._store.pop(key, None)
                        
                    self.commit_id = max(self.commit_id, cid)
                    self.term_id = max(self.term_id, tid)
                except Exception:
                    pass

    def get_logs_since(self, commit_id: int):
        entries = []
        if not os.path.exists(self.filename):
            return entries
        with open(self.filename, 'r') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    entry = json.loads(line.strip())
                    if entry.get("commit_id", 0) > commit_id:
                        entries.append(entry)
                except Exception:
                    pass
        return entries

    def _append_log(self, op: str, key: str, value: Optional[str] = None, commit_id: int = 0, term_id: int = 1):
        entry = {
            "op": op,
            "key": key,
            "value": value,
            "commit_id": commit_id,
            "term_id": term_id
        }
        with open(self.filename, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def put_with_ids(self, key: str, value: str, commit_id: int, term_id: int) -> bool:
        with self._lock:
            self._store[key] = value
            self.commit_id = commit_id
            self.term_id = term_id
            self._append_log("put", key, value, commit_id, term_id)
            return True

    def delete_with_ids(self, key: str, commit_id: int, term_id: int) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                self.commit_id = commit_id
                self.term_id = term_id
                self._append_log("delete", key, None, commit_id, term_id)
                return True
            return False

    def put(self, key: str, value: str) -> bool:
        with self._lock:
            self.commit_id += 1
            return self.put_with_ids(key, value, self.commit_id, self.term_id)

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            return self._store.get(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                self.commit_id += 1
                return self.delete_with_ids(key, self.commit_id, self.term_id)
            return False
