"""Validation SHACL contre le profil `ehds` du catalogue HDH.

Deux niveaux de contrôle, volontairement redondants :

1. `HealthDataset.issues` (ERROR) — accumulé pendant le mapping
   (mapping/dataset.py, mapping/agent.py, mapping/distribution.py), lisible
   sans dépendance à pyshacl et capable de citer la propriété DataHub à
   corriger (G4).
2. `validate_graph()` ci-dessous — l'arbitre final, contre les shapes SHACL
   réelles du HDH. `/ingest` côté HDH ne valide PAS à l'entrée (confirmé lors
   de l'exploration : la validation n'a lieu qu'à la publication) ; c'est
   donc notre unique filet avant tout envoi réseau (P0-5/P0-10).

Le fichier de shapes est empaqueté (`validate/shapes/`) plutôt que lu depuis
`shapes/ehds/` à la racine du dépôt, pour que la validation fonctionne aussi
depuis un wheel installé. `shapes/ehds/` à la racine reste la copie de
référence utilisée pour la resynchronisation avec le HDH (voir son
README) — les deux doivent rester identiques.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

from rdflib import Graph

_SHAPES_RESOURCE = "hdap-validator-sensitivity-shape.ttl"


@dataclass(frozen=True, slots=True)
class ShaclResult:
    conforms: bool
    report_text: str


def _load_shapes_graph() -> Graph:
    shapes = Graph()
    with resources.as_file(resources.files("dh_healthdcat.validate") / "shapes" / _SHAPES_RESOURCE) as path:
        shapes.parse(path, format="turtle")
    return shapes


def validate_graph(data: Graph) -> ShaclResult:
    import pyshacl

    shapes = _load_shapes_graph()
    conforms, _results_graph, report_text = pyshacl.validate(
        data,
        shacl_graph=shapes,
        inference="none",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
    )
    return ShaclResult(conforms=conforms, report_text=report_text)
