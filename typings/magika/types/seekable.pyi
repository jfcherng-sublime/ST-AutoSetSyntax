from _typeshed import Incomplete
from typing import BinaryIO

class Seekable:
    _stream: Incomplete
    _size: Incomplete
    def __init__(self, stream: BinaryIO) -> None: ...
    @property
    def size(self) -> int: ...
    def read_at(self, offset: int, size: int) -> bytes: ...
