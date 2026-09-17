"""reader/graph.py : chargement (et cache) des définitions de structured
properties, et les deux fabriques de connexion `from_env`/`from_config` —
jusqu'ici jamais exercées par la suite (issue #79). `StructuredProperties.list`
est monkeypatché : c'est un appel réseau réel côté acryl-datahub, hors de
portée de `GraphLike` (voir `tests/fixtures/fake_datahub.py::build_context`,
qui court-circuite `_property_definitions` pour la même raison)."""

from __future__ import annotations

from types import SimpleNamespace as NS

from datahub.api.entities.structuredproperties.structuredproperties import StructuredProperties

from dh_healthdcat.reader.graph import ReadContext


def test_property_definitions_are_loaded_indexed_and_cached(monkeypatch):
    calls = []

    def fake_list(graph):
        calls.append(graph)
        return [
            NS(
                qualified_name="fr.aphp.healthdcat.x",
                urn="urn:li:structuredProperty:fr.aphp.healthdcat.x",
                type="urn:li:dataType:datahub.string",
                cardinality="MULTIPLE",
                entity_types=("dataProduct",),
            ),
            # cardinality/entity_types absents : repli sur "SINGLE" / ().
            NS(
                qualified_name="fr.aphp.healthdcat.y",
                urn="urn:li:structuredProperty:fr.aphp.healthdcat.y",
                type="urn:li:dataType:datahub.string",
                cardinality=None,
                entity_types=None,
            ),
            # qualified_name absent : ignorée (prop mal déclarée côté DataHub).
            NS(
                qualified_name=None,
                urn="urn:li:structuredProperty:z",
                type="x",
                cardinality=None,
                entity_types=None,
            ),
        ]

    monkeypatch.setattr(StructuredProperties, "list", staticmethod(fake_list))

    ctx = ReadContext(graph=object())
    definitions = ctx.property_definitions

    assert set(definitions) == {"fr.aphp.healthdcat.x", "fr.aphp.healthdcat.y"}
    assert definitions["fr.aphp.healthdcat.x"].cardinality == "MULTIPLE"
    assert definitions["fr.aphp.healthdcat.y"].cardinality == "SINGLE"
    assert definitions["fr.aphp.healthdcat.y"].entity_types == ()

    # Deuxième accès : pas de second appel à StructuredProperties.list (cache).
    assert ctx.property_definitions is definitions
    assert len(calls) == 1


def test_from_env_wires_the_default_graph_into_a_read_context(monkeypatch):
    sentinel_graph = object()
    monkeypatch.setattr("datahub.ingestion.graph.client.get_default_graph", lambda: sentinel_graph)

    from dh_healthdcat.reader.graph import from_env

    ctx = from_env()

    assert ctx.graph is sentinel_graph


def test_from_config_builds_a_datahub_graph_client_from_server_and_token(monkeypatch):
    captured = {}

    class FakeDataHubGraph:
        def __init__(self, config):
            captured["config"] = config

    monkeypatch.setattr("datahub.ingestion.graph.client.DataHubGraph", FakeDataHubGraph)

    from dh_healthdcat.reader.graph import from_config

    ctx = from_config("https://gms.test", token="tok")

    assert isinstance(ctx.graph, FakeDataHubGraph)
    assert captured["config"].server == "https://gms.test"
    assert captured["config"].token == "tok"
