"""Préfixe des structured properties (SP) HealthDCAT-AP — seul point de déclaration.

Le reader et le mapping ne manipulent que des noms locaux (`healthTheme`,
`legalBasis`, …) ; `qualified()` reconstitue le nom complet là où DataHub
l'attend (URN de la SP) et là où un message doit le montrer à un steward
(voir ADR-0005).

L'ancien préfixe n'est jamais lu (coupure nette, ADR-0005 §2) : il ne sert
qu'à diagnostiquer une instance pas encore migrée.
"""

from __future__ import annotations

from collections.abc import Iterable

SP_PREFIX = "healthdcatap."
LEGACY_PREFIX = "fr.aphp.healthdcat."
MIGRATION_GUIDE = "https://github.com/davidouagne/datahub-healthdcat-ap-exporter/blob/main/docs/migration-0.3.0.md"


def qualified(local_name: str) -> str:
    """Nom qualifié complet d'une SP, ex. `qualified("healthTheme")`."""

    return SP_PREFIX + local_name


def legacy_prefix_error(qualified_names: Iterable[str]) -> str | None:
    """Message d'arrêt si l'instance ne définit que des SP à l'ancien préfixe,
    None sinon (au moins une SP au préfixe courant, ou aucune des deux)."""

    names = list(qualified_names)
    if any(name.startswith(SP_PREFIX) for name in names):
        return None
    legacy = sum(name.startswith(LEGACY_PREFIX) for name in names)
    if not legacy:
        return None
    return (
        f"Cette instance DataHub définit {legacy} structured properties {LEGACY_PREFIX}* "
        f"et aucune {SP_PREFIX}* : l'exporteur ne lit plus que {SP_PREFIX}* (ADR-0005). "
        f"Migrer les définitions et les valeurs avant d'exporter : {MIGRATION_GUIDE}"
    )
