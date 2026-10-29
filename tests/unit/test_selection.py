"""Sélection des DataProducts (selection.py) — docs/specs/feature-tag-filtering.md.

Le filtrage est désormais évalué côté serveur (une requête `get_urns_by_filter`
avec `extra_or_filters`), plus par énumération + test de chaque DataProduct
un par un. Conséquence assumée : le double `FakeGraph` hors ligne ne peut plus
vérifier *quels* DataProducts sortent d'une sélection filtrée (ce serait
réimplémenter la recherche DataHub dans la fixture). On teste donc :

1. `build_selection_query` exhaustivement — fonction pure, elle traduit les
   options CLI en `DataProductQuery` neutre (normalisation, `tag_mode`) ; la
   forme brute du filtre DataHub (OU/ET/exclusion/domaine+tag) est testée à la
   frontière, dans tests/unit/test_reader_graph.py ;
2. `select_data_product_urns` uniquement sur ce qu'on peut observer sans
   réimplémenter la recherche : le nombre d'appels réseau (absence de N+1) et
   la précédence de `--urn`."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import dh_healthdcat.selection as selection_module
from dh_healthdcat.reader.graph import DataProductQuery
from dh_healthdcat.selection import build_selection_query, select_data_product_urns
from tests.fixtures.fake_datahub import ALL_DATAPRODUCT_URNS, build_context


class TestBuildSelectionQuery:
    def test_no_criteria_is_an_empty_query(self):
        assert build_selection_query(domains=[], tags=[]).is_empty

    def test_criteria_are_carried_over_in_neutral_terms(self):
        query = build_selection_query(
            domains=["d1"], tags=["a", "b"], tag_mode="all", exclude_tags=["x"]
        )
        assert query == DataProductQuery(
            domains=("urn:li:domain:d1",),
            tags=("urn:li:tag:a", "urn:li:tag:b"),
            tag_mode="all",
            exclude_tags=("urn:li:tag:x",),
        )

    def test_tag_mode_defaults_to_any(self):
        assert build_selection_query(domains=[], tags=["a"]).tag_mode == "any"

    def test_exclude_tags_alone_is_not_empty(self):
        assert not build_selection_query(domains=[], tags=[], exclude_tags=["x"]).is_empty

    def test_short_names_are_normalized_to_urns(self):
        # "eds" (pas une URN complète) : DataHub exige urn:li:tag:..., voir
        # normalize_tag/normalize_domain — appliqués avant construction du filtre.
        query = build_selection_query(domains=["Biologie"], tags=["eds"])
        assert query.domains == ("urn:li:domain:Biologie",)
        assert query.tags == ("urn:li:tag:eds",)

    def test_full_urns_are_kept_as_is(self):
        query = build_selection_query(
            domains=["urn:li:domain:d1"], tags=["urn:li:tag:a"], exclude_tags=["urn:li:tag:x"]
        )
        assert query.domains == ("urn:li:domain:d1",)
        assert query.tags == ("urn:li:tag:a",)
        assert query.exclude_tags == ("urn:li:tag:x",)

    def test_invalid_tag_mode_raises(self):
        with pytest.raises(ValueError, match="tag_mode"):
            build_selection_query(domains=[], tags=["a"], tag_mode="bogus")


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

        assert result == ALL_DATAPRODUCT_URNS
        assert ctx.graph.get_entity_semityped_calls == []
        assert ctx.graph.last_extra_or_filters is None

    def test_explicit_urn_takes_precedence_no_network_call(self):
        ctx = build_context()
        result = select_data_product_urns(
            ctx, urns=["urn:li:dataProduct:explicit"], domains=[], tags=[]
        )

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
        select_data_product_urns(
            ctx,
            urns=["urn:li:dataProduct:explicit"],
            domains=[],
            tags=[],
            on_warning=warnings.append,
        )

        assert warnings == []

    def test_invalid_tag_mode_propagates(self):
        ctx = build_context()
        with pytest.raises(ValueError, match="tag_mode"):
            select_data_product_urns(ctx, urns=[], domains=[], tags=["a"], tag_mode="bogus")


def test_selection_imports_nothing_from_datahub():
    """ADR-0004 §4 : la sélection reste en termes neutres, seul
    `reader/graph.py` parle à acryl-datahub."""

    tree = ast.parse(Path(selection_module.__file__).read_text(encoding="utf-8"))
    imported = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ] + [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert [name for name in imported if name.split(".")[0] == "datahub"] == []
