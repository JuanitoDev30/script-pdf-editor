"""Historial de deshacer / rehacer basado en instantáneas del PDF completo."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Snapshot:
    data: bytes
    page: int  # página donde ocurrió el cambio, para mostrarla al deshacer/rehacer


class History:
    def __init__(self, limit: int = 30) -> None:
        self.limit = limit
        self._undo: list[Snapshot] = []
        self._redo: list[Snapshot] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def push(self, snapshot: Snapshot) -> None:
        """Registra el estado previo a un cambio nuevo (invalida lo que se podía rehacer)."""
        self._undo.append(snapshot)
        del self._undo[:-self.limit]
        self._redo.clear()

    def discard_last(self) -> Snapshot:
        """Retira la última instantánea sin pasarla a rehacer (cambio cancelado)."""
        return self._undo.pop()

    def undo(self, current: bytes) -> Snapshot | None:
        """Devuelve el estado anterior y guarda `current` para poder rehacer."""
        return self._move(self._undo, self._redo, current)

    def redo(self, current: bytes) -> Snapshot | None:
        return self._move(self._redo, self._undo, current)

    @staticmethod
    def _move(source: list[Snapshot], target: list[Snapshot], current: bytes) -> Snapshot | None:
        if not source:
            return None
        snapshot = source.pop()
        target.append(Snapshot(current, snapshot.page))
        return snapshot

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
