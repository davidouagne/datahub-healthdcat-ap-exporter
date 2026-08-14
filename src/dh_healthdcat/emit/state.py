"""Correspondance URN DataHub -> id HDH, pour l'idempotence des poussées
(G3/P0-8). Fichier JSON simple ; l'alternative "écrite dans DataHub via
structured property" (P1-4, --write-back) n'est pas ce module — voir cli.py."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_STATE_PATH = Path(".dh-healthdcat-state.json")


def load(path: Path = DEFAULT_STATE_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def save(state: dict[str, str], path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True, ensure_ascii=False)


def get_hdh_id(state: dict[str, str], dataset_urn: str) -> str | None:
    return state.get(dataset_urn)


def set_hdh_id(state: dict[str, str], dataset_urn: str, hdh_id: str) -> None:
    state[dataset_urn] = hdh_id


def remove(state: dict[str, str], dataset_urn: str) -> None:
    state.pop(dataset_urn, None)
