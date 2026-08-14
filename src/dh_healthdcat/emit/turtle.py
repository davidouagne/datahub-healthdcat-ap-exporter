"""Sérialisation du graphe HealthDCAT-AP vers un fichier (Lot 2 — P0-4/P1-1/P1-2/P1-3)."""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF, Graph, URIRef

from dh_healthdcat.mapping.namespaces import DCAT, bind_prefixes

FORMAT_TO_RDFLIB = {
    "turtle": "turtle",
    "json-ld": "json-ld",
    "n-triples": "nt",
}
FORMAT_TO_EXTENSION = {
    "turtle": ".ttl",
    "json-ld": ".jsonld",
    "n-triples": ".nt",
}


def write_graph(graph: Graph, output_path: Path, *, fmt: str = "turtle") -> None:
    if fmt not in FORMAT_TO_RDFLIB:
        raise ValueError(f"Format inconnu '{fmt}' (attendu : {', '.join(FORMAT_TO_RDFLIB)})")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output_path), format=FORMAT_TO_RDFLIB[fmt])


def merge_into_catalog(graphs: list[Graph], *, catalog_uri: str, title: str, description: str, publisher_uri: str | None = None) -> Graph:
    """Enveloppe plusieurs graphes dcat:Dataset dans un unique dcat:Catalog
    (P1-3), aligné sur `CatalogSerializer` côté HDH."""

    from rdflib import Literal

    from dh_healthdcat.mapping.namespaces import DCT

    catalog = Graph()
    bind_prefixes(catalog)
    catalog_node = URIRef(catalog_uri)
    catalog.add((catalog_node, RDF.type, DCAT.Catalog))
    catalog.add((catalog_node, DCT.title, Literal(title, lang="fr")))
    catalog.add((catalog_node, DCT.description, Literal(description, lang="fr")))
    if publisher_uri:
        catalog.add((catalog_node, DCT.publisher, URIRef(publisher_uri)))

    for g in graphs:
        for dataset_uri in g.subjects(RDF.type, DCAT.Dataset):
            catalog.add((catalog_node, DCAT.dataset, dataset_uri))
        catalog += g

    return catalog
