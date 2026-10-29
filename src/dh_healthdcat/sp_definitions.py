"""Définitions canoniques des structured properties lues par l'exporteur.

Ce dépôt en est la source de vérité (ADR-0005 §3) : `sp_definitions.yml`,
embarqué dans le paquet, porte les noms locaux, types, cardinalités et types
d'entités. `write()` les sérialise au format natif de `datahub properties
upsert -f`, en ajoutant le préfixe de `sp.py` et en générant les valeurs
autorisées depuis le vocabulaire nommé : elles ne peuvent pas diverger de ce
que le reader résout. L'exporteur reste en lecture seule sur DataHub ; c'est
l'adoptant qui applique le fichier.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from dh_healthdcat import sp
from dh_healthdcat.mapping import vocabularies

DEFINITIONS_FILE = Path(__file__).with_name("sp_definitions.yml")
DEFAULT_FILE_NAME = "structured-properties.yml"


@dataclass(frozen=True, slots=True)
class Definition:
    name: str
    display_name: str
    description: str
    type: str  # string | rich_text | number | date
    cardinality: str  # SINGLE | MULTIPLE
    entity_types: tuple[str, ...]
    vocabulary: str | None = None


@cache
def definitions() -> tuple[Definition, ...]:
    with DEFINITIONS_FILE.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return tuple(
        Definition(**{**entry, "entity_types": tuple(entry["entity_types"])}) for entry in raw
    )


def to_upsert(definition: Definition) -> dict[str, Any]:
    """Une entrée du format `datahub properties upsert`."""

    entry: dict[str, Any] = {
        "id": sp.qualified(definition.name),
        "display_name": definition.display_name,
        "description": definition.description,
        "type": definition.type,
        "cardinality": definition.cardinality,
        "entity_types": list(definition.entity_types),
    }
    if definition.vocabulary is not None:
        vocabulary = vocabularies.load(definition.vocabulary)
        entry["allowed_values"] = [
            {"value": code, "description": vocabulary.labels_fr[code]}
            if code in vocabulary.labels_fr
            else {"value": code}
            for code in vocabulary.code_to_uri
        ]
    return entry


def write(output: Path) -> Path:
    """Écrit toutes les définitions dans `output` (fichier, ou répertoire qui
    reçoit `structured-properties.yml`) et renvoie le chemin écrit."""

    path = output / DEFAULT_FILE_NAME if output.is_dir() else output
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = [to_upsert(d) for d in definitions()]
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(entries, fh, allow_unicode=True, sort_keys=False, width=100)
    return path
