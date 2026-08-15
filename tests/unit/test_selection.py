"""Sélection des DataProducts (selection.py) — spec/spec-feature-tag-filtering.md.

Le filtrage est désormais évalué côté serveur (une requête `get_urns_by_filter`
avec `extra_or_filters`), plus par énumération + test de chaque DataProduct
un par un. Conséquence assumée : le double `FakeGraph` hors ligne ne peut plus
vérifier *quels* DataProducts sortent d'une sélection filtrée (ce serait
réimplémenter la recherche DataHub dans la fixture). On teste donc :

1. `build_selection_filter` exhaustivement — c'est une fonction pure, elle
   porte toute la sémantique (OU/ET/exclusion/domaine+tag) et ne dépend ni de
   `ReadContext` ni du réseau ;
2. `select_data_product_urns` uniquement sur ce qu'on peut observer sans
   réimplémenter la recherche : le nombre d'appels réseau (absence de N+1) et
   la précédence de `--urn`."""

from __future__ import annotations

import pytest

from dh_healthdcat.selection import build_selection_filter, select_data_product_urns
from tests.fixtures.fake_datahub import DATAPRODUCT_URN, build_context


class TestBuildSelectionFilter:
    def test_no_criteria_returns_none(self):
        assert build_selection_filter(domains=[], tags=[]) is None

    def test_domain_only(self):
        assert build_selection_filter(domains=["d1"], tags=[]) == [
            {"and": [{"field": "domains", "condition": "EQUAL", "values": ["urn:li:domain:d1"]}]}
        ]

    def test_tags_any_is_a_single_or_rule(self):
        # tag_mode="any" (défaut) : une seule règle multi-valeurs, OU implicite
        # au niveau de la recherche — reproduit exactement le comportement v0.
        assert build_selection_filter(domains=[], tags=["a", "b"]) == [
            {"and": [{"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:a", "urn:li:tag:b"]}]}
        ]

    def test_tags_all_is_one_rule_per_tag_anded(self):
        result = build_selection_filter(domains=[], tags=["a", "b"], tag_mode="all")
        assert result == [
            {
                "and": [
                    {"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:a"]},
                    {"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:b"]},
                ]
            }
        ]

    def test_exclude_tags_is_a_single_negated_rule(self):
        result = build_selection_filter(domains=[], tags=[], exclude_tags=["x"])
        assert result == [{"and": [{"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:x"], "negated": True}]}]

    def test_domain_and_tag_combine_with_and(self):
        result = build_selection_filter(domains=["d1"], tags=["a"])
        assert result == [
            {
                "and": [
                    {"field": "domains", "condition": "EQUAL", "values": ["urn:li:domain:d1"]},
                    {"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:a"]},
                ]
            }
        ]

    def test_short_names_are_normalized_to_urns(self):
        # "eds" (pas une URN complète) : FilterDsl exige urn:li:tag:..., voir
        # normalize_tag/normalize_domain — appliqués avant construction du filtre.
        result = build_selection_filter(domains=["Biologie"], tags=["eds"])
        domain_rule, tag_rule = result[0]["and"]
        assert domain_rule["values"] == ["urn:li:domain:Biologie"]
        assert tag_rule["values"] == ["urn:li:tag:eds"]

    def test_invalid_tag_mode_raises(self):
        with pytest.raises(ValueError, match="tag_mode"):
            build_selection_filter(domains=[], tags=["a"], tag_mode="bogus")


class TestSelectDataProductUrns:
    def test_filtered_selection_makes_a_single_search_call_no_per_entity_lookup(self):
        """REQ-001 : le coût réseau d'une sélection filtrée ne dépend plus du
        nombre de DataProducts du catalogue — aucun `get_entity_semityped`
        pendant la sélection, un seul `get_urns_by_filter`."""

        ctx = build_context()
        select_data_product_urns(ctx, urns=[], domains=[], tags=["access"])

        assert ctx.graph.get_entity_semityped_calls == []
        assert ctx.graph.last_extra_or_filters == [
            {"and": [{"field": "tags", "condition": "EQUAL", "values": ["urn:li:tag:access"]}]}
        ]

    def test_unfiltered_selection_still_makes_a_single_search_call(self):
        ctx = build_context()
        result = select_data_product_urns(ctx, urns=[], domains=[], tags=[])

        assert result == [DATAPRODUCT_URN]
        assert ctx.graph.get_entity_semityped_calls == []
        assert ctx.graph.last_extra_or_filters is None

    def test_explicit_urn_takes_precedence_no_network_call(self):
        ctx = build_context()
        result = select_data_product_urns(ctx, urns=["urn:li:dataProduct:explicit"], domains=[], tags=[])

        assert result == ["urn:li:dataProduct:explicit"]
        assert ctx.graph.get_entity_semityped_calls == []
        assert ctx.graph.last_extra_or_filters is None  # get_urns_by_filter jamais appelé

    def test_explicit_urn_with_filters_warns_and_ignores_filters(self):
        ctx = build_context()
        warnings: list[str] = []
        result = select_data_product_urns(
            ctx,
            urns=["urn:li:dataProduct:explicit"],
            domains=[],
            tags=["access"],
            on_warning=warnings.append,
        )

        assert result == ["urn:li:dataProduct:explicit"]
        assert len(warnings) == 1
        assert "--urn" in warnings[0]

    def test_no_warning_when_urn_given_without_filters(self):
        ctx = build_context()
        warnings: list[str] = []
        select_data_product_urns(ctx, urns=["urn:li:dataProduct:explicit"], domains=[], tags=[], on_warning=warnings.append)

        assert warnings == []

    def test_invalid_tag_mode_propagates(self):
        ctx = build_context()
        with pytest.raises(ValueError, match="tag_mode"):
            select_data_product_urns(ctx, urns=[], domains=[], tags=["a"], tag_mode="bogus")
