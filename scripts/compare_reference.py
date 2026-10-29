"""Compare un export Turtle à la référence commitée, par isomorphisme RDF.

    uv run python scripts/compare_reference.py <export.ttl> <reference.ttl> [--update]

Sort en 0 si les deux graphes sont isomorphes, en 1 sinon, avec les triples
présents d'un seul côté (N-Triples triés, donc un diff lisible). `--update`
réécrit la référence à partir de l'export (Turtle trié, stable en revue).

Aucune normalisation n'est appliquée : le seed fixe toutes les dates
(tests/integration/seed/) et les URI de nœuds sont des uuid5 déterministes
(mapping/nodes.py). Si une valeur dépendant de l'ingestion apparaît un jour,
la normaliser ici et la documenter (#130).
"""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph
from rdflib.compare import graph_diff, to_isomorphic


def _load(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def _ntriples(graph: Graph) -> list[str]:
    return sorted(line for line in graph.serialize(format="nt").splitlines() if line.strip())


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--update"]
    if len(args) != 2:  # noqa: PLR2004 - export + référence
        print(__doc__, file=sys.stderr)
        return 2
    export_path, reference_path = (Path(a) for a in args)
    actual = _load(export_path)

    if "--update" in argv:
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        reference_path.write_text(actual.serialize(format="turtle"), encoding="utf-8")
        print(f"Référence réécrite : {reference_path} ({len(actual)} triples)")
        return 0

    if not reference_path.exists():
        print(f"Référence absente : {reference_path} (relancer avec --update-reference)")
        return 1
    expected = _load(reference_path)

    iso_actual, iso_expected = to_isomorphic(actual), to_isomorphic(expected)
    if iso_actual == iso_expected:
        print(f"Identique à la référence ({len(actual)} triples).")
        return 0

    _, only_actual, only_expected = graph_diff(iso_actual, iso_expected)
    print(f"Différent de la référence {reference_path} :")
    for line in _ntriples(only_expected):
        print(f"- {line}")
    for line in _ntriples(only_actual):
        print(f"+ {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
