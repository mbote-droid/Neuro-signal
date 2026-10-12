"""A small name -> factory registry used for readers and methods."""

from __future__ import annotations

from collections.abc import Callable


class Registry[T]:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._items: dict[str, T] = {}

    def register(self, key: str) -> Callable[[T], T]:
        def deco(obj: T) -> T:
            if key in self._items:
                raise ValueError(f"duplicate {self.kind} {key!r}")
            self._items[key] = obj
            return obj

        return deco

    def get(self, key: str) -> T:
        try:
            return self._items[key]
        except KeyError:
            raise KeyError(f"unknown {self.kind} {key!r}; known: {sorted(self._items)}") from None

    def keys(self) -> list[str]:
        return sorted(self._items)
