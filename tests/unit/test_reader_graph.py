"""reader/graph.py : chargement (et cache) des définitions de structured
properties, et les deux fabriques de connexion `from_env`/`from_config` —
jusqu'ici jamais exercées par la suite (issue #79). `StructuredProperties.list`
est monkeypatché : c'est un appel réseau réel côté acryl-datahub, hors de
portée de `GraphLike` (voir `tests/fixtures/fake_datahub.py::build_context`,
qui court-circuite `_property_definitions` pour la même raison)."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from datahub.api.entities.structuredproperties.structuredproperties import StructuredProperties

from dh_healthdcat.reader.graph import (
    ASPECTS_READ,
    DataProductQuery,
    ReadContext,
    to_datahub_filter,
)
from tests.fixtures.fake_datahub import ALL_DATAPRODUCT_URNS, DATAPRODUCT_URN, build_context


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


class TestToDatahubFilter:
    """Forme brute `extra_or_filters` produite via `FilterDsl` — la zone la plus
    fragile d'une version d'acryl-datahub à l'autre, d'où des attentes exactes."""

    def test_empty_query_returns_none(self):
        assert to_datahub_filter(DataProductQuery()) is None

    def test_domain_only(self):
        assert to_datahub_filter(DataProductQuery(domains=("urn:li:domain:d1",))) == [
            {"and": [{"field": "domains", "condition": "EQUAL", "values": ["urn:li:domain:d1"]}]}
        ]

    def test_tags_any_is_a_single_or_rule(self):
        # tag_mode="any" (défaut) : une seule règle multi-valeurs, OU implicite
        # au niveau de la recherche — reproduit exactement le comportement v0.
        query = DataProductQuery(tags=("urn:li:tag:a", "urn:li:tag:b"))
        assert to_datahub_filter(query) == [
            {
                "and": [
                    {
                        "field": "tags",
                        "condition": "EQUAL",
                        "values": ["urn:li:tag:a", "urn:li:tag:b"],
                    }
                ]
            }
        ]

    def test_tags_all_is_one_rule_per_tag_anded(self):
        query = DataProductQuery(tags=("urn:li:tag:a", "urn:li:tag:b"), tag_mode="all")
        assert to_datahub_filter(query) == [
            {
                "and": [
                    {"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:a"]},
                    {"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:b"]},
                ]
            }
        ]

    def test_exclude_tags_is_a_single_negated_rule(self):
        assert to_datahub_filter(DataProductQuery(exclude_tags=("urn:li:tag:x",))) == [
            {
                "and": [
                    {
                        "field": "tags",
                        "condition": "EQUAL",
                        "values": ["urn:li:tag:x"],
                        "negated": True,
                    }
                ]
            }
        ]

    def test_domain_and_tag_combine_with_and(self):
        query = DataProductQuery(domains=("urn:li:domain:d1",), tags=("urn:li:tag:a",))
        assert to_datahub_filter(query) == [
            {
                "and": [
                    {"field": "domains", "condition": "EQUAL", "values": ["urn:li:domain:d1"]},
                    {"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:a"]},
                ]
            }
        ]


class TestFindDataProductUrns:
    def test_passes_the_translated_filter_in_a_single_search(self):
        ctx = build_context()
        result = ctx.find_data_product_urns(DataProductQuery(tags=("urn:li:tag:a",)))

        assert result == ALL_DATAPRODUCT_URNS
        assert ctx.graph.last_extra_or_filters == [
            {"and": [{"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:a"]}]}
        ]
        assert ctx.graph.get_entity_semityped_calls == []

    def test_empty_query_searches_without_filter(self):
        ctx = build_context()
        ctx.find_data_product_urns(DataProductQuery())

        assert ctx.graph.last_extra_or_filters is None


class TestGetEntity:
    def test_requests_the_declared_aspects_for_the_entity_type(self):
        ctx = build_context()
        ctx.get_entity(DATAPRODUCT_URN)

        assert ctx.graph.requested_aspects[DATAPRODUCT_URN] == list(ASPECTS_READ["dataProduct"])

    def test_entity_is_fetched_once(self):
        ctx = build_context()
        ctx.get_entity(DATAPRODUCT_URN)
        ctx.get_entity(DATAPRODUCT_URN)

        assert ctx.graph.get_entity_semityped_calls == [DATAPRODUCT_URN]

    def test_undeclared_entity_type_fails_loudly(self):
        with pytest.raises(ValueError, match="ASPECTS_READ"):
            build_context().get_entity("urn:li:corpuser:jdoe")

    def test_invalid_urn_is_rejected(self):
        with pytest.raises(ValueError, match="URN DataHub invalide"):
            build_context().get_entity("pas-une-urn")
