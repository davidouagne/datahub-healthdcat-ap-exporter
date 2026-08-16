"""Double minimal du catalogue HDH : implémente `HdhTarget`
(emit/hdh_client.py) en mémoire, sans réseau — l'adapter que
`pipeline.push()` traverse dans les tests, aux côtés de `HdhClient` (réseau,
production). Sert de fixture partagée à tests/unit/test_push.py.

`created`/`updated` enregistrent chaque appel pour affirmer qu'aucune écriture
n'a lieu pour un jeu invalide ou en `--dry-run`. `fail_next_creates`/
`fail_next_updates` font échouer les N prochains appels correspondants avec
`HdhClientError`, pour tester qu'un échec réseau isolé sur un jeu n'empêche
pas les jeux suivants d'être poussés (story 13)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from dh_healthdcat.emit.hdh_client import HdhClientError


@dataclass
class InMemoryHdhCatalog:
    created: list[str] = field(default_factory=list)  # turtle bodies POSTés
    updated: list[tuple[str, str]] = field(default_factory=list)  # (original_id, turtle)
    fail_next_creates: int = 0
    fail_next_updates: int = 0

    def create_dataset(self, turtle: str) -> str:
        if self.fail_next_creates > 0:
            self.fail_next_creates -= 1
            raise HdhClientError(500, "échec simulé (create)")
        self.created.append(turtle)
        return f"hdh-{uuid.uuid4()}"

    def update_dataset(self, original_id: str, turtle: str) -> str:
        if self.fail_next_updates > 0:
            self.fail_next_updates -= 1
            raise HdhClientError(500, "échec simulé (update)")
        self.updated.append((original_id, turtle))
        return original_id
