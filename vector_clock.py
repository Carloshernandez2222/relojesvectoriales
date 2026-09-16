"""Reloj vectorial para un sistema distribuido.

Cada componente del vector corresponde a un nodo. Las reglas usadas son:

- Evento local o envío: se incrementa solo la posición propia.
- Recepción: se toma el máximo componente a componente con el reloj
  recibido y después se incrementa la posición propia.
"""

from __future__ import annotations

from typing import Mapping


class VectorClock:
    """Reloj vectorial indexado por identificador de nodo."""

    def __init__(self, node_ids: list[str], owner: str) -> None:
        if owner not in node_ids:
            raise ValueError(f"El nodo {owner} no está en {node_ids}")
        self.owner = owner
        self._clock = {node_id: 0 for node_id in node_ids}

    def copy(self) -> dict[str, int]:
        """Devuelve una copia del vector actual."""
        return dict(self._clock)

    def increment(self) -> dict[str, int]:
        """Incrementa la posición propia (evento local o envío)."""
        self._clock[self.owner] += 1
        return self.copy()

    def merge(self, other: Mapping[str, int]) -> dict[str, int]:
        """Combina con otro reloj usando el máximo componente a componente."""
        for node_id in self._clock:
            incoming = int(other.get(node_id, 0))
            self._clock[node_id] = max(self._clock[node_id], incoming)
        return self.copy()

    def on_receive(self, other: Mapping[str, int]) -> dict[str, int]:
        """Actualiza el reloj al recibir un mensaje: max() y luego incrementa."""
        self.merge(other)
        return self.increment()

    @staticmethod
    def happens_before(left: Mapping[str, int], right: Mapping[str, int]) -> bool:
        """True si left → right (left ocurrió antes que right de forma causal)."""
        keys = set(left) | set(right)
        less_or_equal = all(int(left.get(k, 0)) <= int(right.get(k, 0)) for k in keys)
        strictly_less = any(int(left.get(k, 0)) < int(right.get(k, 0)) for k in keys)
        return less_or_equal and strictly_less

    @staticmethod
    def concurrent(left: Mapping[str, int], right: Mapping[str, int]) -> bool:
        """True si los dos eventos son concurrentes (no hay relación causal)."""
        return not VectorClock.happens_before(left, right) and not VectorClock.happens_before(
            right, left
        )

    def __str__(self) -> str:
        ordered = ", ".join(f"{k}:{self._clock[k]}" for k in sorted(self._clock))
        return f"[{ordered}]"
