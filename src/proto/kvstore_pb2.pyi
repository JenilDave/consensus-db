from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PutRequest(_message.Message):
    __slots__ = ("key", "value", "commit_id", "term_id")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    COMMIT_ID_FIELD_NUMBER: _ClassVar[int]
    TERM_ID_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: str
    commit_id: int
    term_id: int
    def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ..., commit_id: _Optional[int] = ..., term_id: _Optional[int] = ...) -> None: ...

class PutResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ...) -> None: ...

class GetRequest(_message.Message):
    __slots__ = ("key",)
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: str
    def __init__(self, key: _Optional[str] = ...) -> None: ...

class GetResponse(_message.Message):
    __slots__ = ("found", "value")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    found: bool
    value: str
    def __init__(self, found: _Optional[bool] = ..., value: _Optional[str] = ...) -> None: ...

class DeleteRequest(_message.Message):
    __slots__ = ("key", "commit_id", "term_id")
    KEY_FIELD_NUMBER: _ClassVar[int]
    COMMIT_ID_FIELD_NUMBER: _ClassVar[int]
    TERM_ID_FIELD_NUMBER: _ClassVar[int]
    key: str
    commit_id: int
    term_id: int
    def __init__(self, key: _Optional[str] = ..., commit_id: _Optional[int] = ..., term_id: _Optional[int] = ...) -> None: ...

class DeleteResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ...) -> None: ...

class SyncRequest(_message.Message):
    __slots__ = ("from_commit_id",)
    FROM_COMMIT_ID_FIELD_NUMBER: _ClassVar[int]
    from_commit_id: int
    def __init__(self, from_commit_id: _Optional[int] = ...) -> None: ...

class SyncEntry(_message.Message):
    __slots__ = ("op", "key", "value", "commit_id", "term_id")
    OP_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    COMMIT_ID_FIELD_NUMBER: _ClassVar[int]
    TERM_ID_FIELD_NUMBER: _ClassVar[int]
    op: str
    key: str
    value: str
    commit_id: int
    term_id: int
    def __init__(self, op: _Optional[str] = ..., key: _Optional[str] = ..., value: _Optional[str] = ..., commit_id: _Optional[int] = ..., term_id: _Optional[int] = ...) -> None: ...

class SyncResponse(_message.Message):
    __slots__ = ("entries",)
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[SyncEntry]
    def __init__(self, entries: _Optional[_Iterable[_Union[SyncEntry, _Mapping]]] = ...) -> None: ...
