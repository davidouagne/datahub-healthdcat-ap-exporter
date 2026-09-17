"""emit/turtle.py : sérialisation sur disque et fusion multi-graphes en un
dcat:Catalog — jusqu'ici jamais exercé par la suite (issue #79)."""

from __future__ import annotations

import pytest
from rdflib import RDF, Graph, Literal, URIRef

from dh_healthdcat.emit.turtle import merge_into_catalog, write_graph
from dh_healthdcat.mapping.namespaces import DCAT, DCT


def _dataset_graph(dataset_uri: str, label: str) -> Graph:
    g = Graph()
    node = URIRef(dataset_uri)
    g.add((node, RDF.type, DCAT.Dataset))
    g.add((node, DCT.title, Literal(label, lang="fr")))
    return g


def test_write_graph_turtle_creates_missing_parent_dirs_and_is_reparseable(tmp_path):
    graph = _dataset_graph("urn:test:dataset:1", "Jeu 1")
    output_path = tmp_path / "nested" / "sub" / "out.ttl"

    write_graph(graph, output_path)

    assert output_path.is_file()
    reparsed = Graph().parse(str(output_path), format="turtle")
    assert len(reparsed) == len(graph)


def test_write_graph_json_ld(tmp_path):
    graph = _dataset_graph("urn:test:dataset:1", "Jeu 1")
    output_path = tmp_path / "out.jsonld"

    write_graph(graph, output_path, fmt="json-ld")

    reparsed = Graph().parse(str(output_path), format="json-ld")
    assert len(reparsed) == len(graph)


def test_write_graph_n_triples(tmp_path):
    graph = _dataset_graph("urn:test:dataset:1", "Jeu 1")
    output_path = tmp_path / "out.nt"

    write_graph(graph, output_path, fmt="n-triples")

    reparsed = Graph().parse(str(output_path), format="nt")
    assert len(reparsed) == len(graph)


def test_write_graph_unknown_format_raises(tmp_path):
    graph = _dataset_graph("urn:test:dataset:1", "Jeu 1")

    with pytest.raises(ValueError, match="bogus"):
        write_graph(graph, tmp_path / "out.bogus", fmt="bogus")


def test_merge_into_catalog_wraps_datasets_and_preserves_their_triples():
    g1 = _dataset_graph("urn:test:dataset:1", "Jeu 1")
    g2 = _dataset_graph("urn:test:dataset:2", "Jeu 2")

    catalog = merge_into_catalog(
        [g1, g2],
        catalog_uri="urn:test:catalog",
        title="Catalogue",
        description="Un catalogue de test",
        publisher_uri="urn:test:publisher",
    )

    catalog_node = URIRef("urn:test:catalog")
    assert (catalog_node, RDF.type, DCAT.Catalog) in catalog
    assert (catalog_node, DCT.title, Literal("Catalogue", lang="fr")) in catalog
    assert (catalog_node, DCT.description, Literal("Un catalogue de test", lang="fr")) in catalog
    assert (catalog_node, DCT.publisher, URIRef("urn:test:publisher")) in catalog
    assert (catalog_node, DCAT.dataset, URIRef("urn:test:dataset:1")) in catalog
    assert (catalog_node, DCAT.dataset, URIRef("urn:test:dataset:2")) in catalog
    # Les triples propres de chaque graphe source restent présents.
    assert (URIRef("urn:test:dataset:1"), DCT.title, Literal("Jeu 1", lang="fr")) in catalog
    assert (URIRef("urn:test:dataset:2"), DCT.title, Literal("Jeu 2", lang="fr")) in catalog


def test_merge_into_catalog_without_publisher_omits_the_triple():
    g1 = _dataset_graph("urn:test:dataset:1", "Jeu 1")

    catalog = merge_into_catalog(
        [g1], catalog_uri="urn:test:catalog", title="Catalogue", description="Description"
    )

    assert list(catalog.objects(URIRef("urn:test:catalog"), DCT.publisher)) == []
