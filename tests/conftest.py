"""Hermétisme de la suite vis-à-vis de l'environnement du poste (REQ-011,
spec/spec-feature-catalogue-instance-config.md) : un développeur ayant
exporté `HDH_API_KEY`/`HDH_URL`/`HDH_PROFILE`/`HDH_CONFIG` dans son shell ne
doit obtenir aucun résultat différent de `uv run pytest`."""

from __future__ import annotations

import pytest

_HDH_ENV_VARS = ("HDH_API_KEY", "HDH_URL", "HDH_PROFILE", "HDH_CONFIG")


@pytest.fixture(autouse=True)
def _hermetic_hdh_env(monkeypatch):
    for name in _HDH_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
