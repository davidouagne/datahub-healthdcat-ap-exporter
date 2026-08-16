"""État de poussée : correspondance URN DataHub -> id HDH, pour l'idempotence
des poussées (G3/P0-8). L'alternative "écrite dans DataHub via structured
property" (P1-4, --write-back) n'est pas ce module — voir cli.py.

`PushState` possède son chemin et sa politique de persistance : `record()`
écrit sur disque immédiatement, en écriture atomique (fichier temporaire puis
`os.replace`), plutôt que de laisser l'appelant décider quand sauvegarder.
Une poussée interrompue en cours de lot ne perd donc que le jeu en cours, pas
les ids déjà attribués (spec-feature-export-pipeline.md, stories 8/12/18)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_STATE_PATH = Path(".dh-healthdcat-state.json")


@dataclass(slots=True)
class PushState:
    path: Path
    _ids: dict[str, str] = field(default_factory=dict)

    @classmethod
    def open(cls, path: Path = DEFAULT_STATE_PATH) -> PushState:
        if not path.exists():
            return cls(path=path)
        with path.open(encoding="utf-8") as fh:
            return cls(path=path, _ids=json.load(fh))

    def hdh_id_for(self, dataset_urn: str) -> str | None:
        return self._ids.get(dataset_urn)

    def record(self, dataset_urn: str, hdh_id: str) -> None:
        """Enregistre l'id et persiste immédiatement sur disque."""

        self._ids[dataset_urn] = hdh_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(self._ids, fh, indent=2, sort_keys=True, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, self.path)
