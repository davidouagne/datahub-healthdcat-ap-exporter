"""Contrôle de la version du serveur DataHub au démarrage (ADR-0004 §5).

La plage des *Versions DataHub supportées* n'est déclarée qu'une fois, dans
`pyproject.toml` (contrainte `acryl-datahub`, plage serveur = plage client) ;
elle est relue ici depuis les métadonnées du paquet installé, jamais recopiée.

Hors plage, version non reconnue ou DataHub Cloud : un message explicite, que
la CLI affiche en avertissement, ou en erreur avec `--strict-version`.
"""

from __future__ import annotations

import re
from importlib.metadata import requires

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version

from dh_healthdcat.reader.graph import ServerInfo

DISTRIBUTION = "dh-healthdcat"
CLIENT_DISTRIBUTION = "acryl-datahub"

# `v1.7.0.1`, `1.8.0rc2`, `v1.7.0.1-SNAPSHOT` → partie numérique en tête.
_LEADING_VERSION = re.compile(r"^v?(\d+(?:\.\d+)*)")


def supported_range() -> SpecifierSet:
    """Contrainte `acryl-datahub` déclarée par le paquet installé."""

    for raw in requires(DISTRIBUTION) or []:
        requirement = Requirement(raw)
        if canonicalize_name(requirement.name) == CLIENT_DISTRIBUTION and (
            requirement.marker is None
        ):
            return requirement.specifier
    raise RuntimeError(f"{DISTRIBUTION} ne déclare pas de dépendance {CLIENT_DISTRIBUTION}")


def check(server: ServerInfo, supported: SpecifierSet) -> str | None:
    """None si le serveur est dans la plage, sinon le message à afficher."""

    unrecognized = (
        f"Version du serveur DataHub non reconnue ({{}}) : compatibilité non vérifiée, "
        f"plage supportée {supported}."
    )
    if server.is_cloud:
        return unrecognized.format("DataHub Cloud")
    if server.unreachable:
        return unrecognized.format("/config inaccessible")
    if server.version is None:
        return unrecognized.format("absente de /config")

    match = _LEADING_VERSION.match(server.version.strip())
    if match is None:
        return unrecognized.format(f"« {server.version} » illisible")
    if Version(match.group(1)) in supported:
        return None
    return (
        f"Serveur DataHub {server.version} hors de la plage supportée ({supported}) : "
        "export non garanti. --strict-version pour échouer dans ce cas."
    )
