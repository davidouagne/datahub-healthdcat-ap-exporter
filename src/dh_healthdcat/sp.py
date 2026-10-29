"""Préfixe des structured properties (SP) HealthDCAT-AP — seul point de déclaration.

Le reader et le mapping ne manipulent que des noms locaux (`healthTheme`,
`legalBasis`, …) ; `qualified()` reconstitue le nom complet là où DataHub
l'attend (URN de la SP) et là où un message doit le montrer à un steward
(voir ADR-0005).
"""

from __future__ import annotations

SP_PREFIX = "fr.aphp.healthdcat."


def qualified(local_name: str) -> str:
    """Nom qualifié complet d'une SP, ex. `qualified("healthTheme")`."""

    return SP_PREFIX + local_name
