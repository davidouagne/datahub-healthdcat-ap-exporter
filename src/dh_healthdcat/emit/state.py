"""État de poussée : correspondance URN DataHub -> id HDH, pour l'idempotence
des poussées (G3/P0-8), cloisonnée par instance de catalogue —
spec/spec-feature-catalogue-instance-config.md, REQ-008/009. L'alternative
"écrite dans DataHub via structured property" (P1-4, --write-back) n'est pas
ce module — voir cli.py.

`PushState` possède son chemin et sa politique de persistance : `record()`
écrit sur disque immédiatement, en écriture atomique (fichier temporaire puis
`os.replace`), plutôt que de laisser l'appelant décider quand sauvegarder.
Une poussée interrompue en cours de lot ne perd donc que le jeu en cours, pas
les ids déjà attribués (spec-feature-export-pipeline.md, stories 8/12/18).

Le document en mémoire (et sur disque) porte tous les compartiments
(`{"version": 2, "instances": {url normalisée: {urn: id}}}`), pas seulement
celui de l'instance courante : `record()` ne réécrit que son propre
compartiment, jamais celui d'une autre instance qui partagerait le même
fichier (REQ-102 — relecture-fusion concurrente — reste hors périmètre : ce
n'est sûr qu'en l'absence d'écriture concurrente entre `open()` et
`record()`)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

DEFAULT_STATE_PATH = Path(".dh-healthdcat-state.json")
_FORMAT_VERSION = 2


@dataclass(slots=True)
class PushState:
    path: Path
    instance: str
    _document: dict = field(default_factory=lambda: {"version": _FORMAT_VERSION, "instances": {}})

    @classmethod
    def open(
        cls,
        path: Path = DEFAULT_STATE_PATH,
        *,
        instance: str,
        on_warning: Callable[[str], None] | None = None,
    ) -> PushState:
        """`instance` doit être l'URL normalisée par
        `dh_healthdcat.config.normalize_url` — c'est elle qui cloisonne les
        ids d'une instance à l'autre."""

        if not path.exists():
            return cls(path=path, instance=instance)

        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)

        if "version" in raw:
            return cls(path=path, instance=instance, _document=raw)

        # Format historique plat {urn: id} (REQ-009) : repris en mémoire sous
        # l'instance courante, sans aucune écriture ici — le fichier reste
        # octet pour octet identique tant que record() n'a pas eu lieu, donc
        # un --dry-run ne le modifie pas.
        if on_warning is not None and raw:
            on_warning(f"État de poussée au format historique repris sous l'instance {instance!r} ({len(raw)} id(s)).")
        document = {"version": _FORMAT_VERSION, "instances": {instance: dict(raw)}}
        return cls(path=path, instance=instance, _document=document)

    def hdh_id_for(self, dataset_urn: str) -> str | None:
        return self._document["instances"].get(self.instance, {}).get(dataset_urn)

    def record(self, dataset_urn: str, hdh_id: str) -> None:
        """Enregistre l'id et persiste immédiatement sur disque — uniquement
        le compartiment de l'instance courante ; les autres compartiments déjà
        chargés en mémoire depuis `open()` sont réécrits tels quels."""

        bucket = self._document["instances"].setdefault(self.instance, {})
        bucket[dataset_urn] = hdh_id

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(self._document, fh, indent=2, sort_keys=True, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, self.path)
