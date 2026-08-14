"""Convention d'URI des nœuds, reproduite du sérialiseur HDH (`to_turtle()`).

Le HDH adresse ses sous-ressources par des URI non déréférençables du type
`<dataset:{uuid}>`, `<publisher:{uuid}>`, `<distribution:{uuid}>` — un "schéma"
`{kind}:` suivi d'un UUID, pas une URL sur un domaine. On reproduit cette
convention pour rester visuellement cohérent avec ce que le HDH produit
lui-même (`api/app/tests/files/test.ttl` en est l'étalon).

Le serveur régénère de toute façon tous les UUID imbriqués à l'ingestion
(`_full_dataset_from_turtle_string`) : seule la stabilité *au sein d'un même
export* compte, pour que deux exécutions successives sur un catalogue inchangé
produisent un Turtle identique (diffable, testable). D'où `uuid5` déterministe
plutôt que `uuid4` aléatoire.
"""

from __future__ import annotations

import uuid

from rdflib import URIRef

# Espace de noms UUID arbitraire mais fixe, dédié à ce projet.
_SEED_NAMESPACE = uuid.UUID("f26a1c9e-6e3b-4a63-9e33-9c1a9f4a9c8a")


def stable_id(*parts: str) -> str:
    """UUID déterministe à partir d'une ou plusieurs chaînes (ex. URN + rôle)."""

    return str(uuid.uuid5(_SEED_NAMESPACE, "|".join(parts)))


def node_uri(kind: str, *seed_parts: str) -> URIRef:
    """`<{kind}:{uuid5(seed_parts)}>` — ex. node_uri("publisher", dataset_urn)."""

    return URIRef(f"{kind}:{stable_id(*seed_parts)}")
