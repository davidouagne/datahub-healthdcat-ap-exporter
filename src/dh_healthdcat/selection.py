"""Sélection des DataProducts à traiter — partagée par `export-file` et
`push-hdh` (cli.py) pour que les deux commandes filtrent (--urn/--domain/--tag)
de façon identique.

Voir spec/spec-feature-tag-filtering.md : le filtre est évalué côté serveur
(une seule requête `get_urns_by_filter`), pas en énumérant tout le catalogue
puis en testant chaque DataProduct un par un (coût en O(N) du v0, corrigé
ici) — d'où la séparation entre `build_selection_filter` (pure, testable hors
ligne) et `select_data_product_urns` (l'appel réseau proprement dit)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from dh_healthdcat.reader.graph import ReadContext

TagMode = Literal["any", "all"]

_URN_PRECEDENCE_WARNING = (
    "--urn a été fourni : --domain/--tag/--exclude-tag sont ignorés "
    "(--urn est prioritaire, voir spec/spec-feature-tag-filtering.md)."
)


def normalize_domain(value: str) -> str:
    return value if value.startswith("urn:li:domain:") else f"urn:li:domain:{value}"


def normalize_tag(value: str) -> str:
    return value if value.startswith("urn:li:tag:") else f"urn:li:tag:{value}"


def build_selection_filter(
    *,
    domains: list[str],
    tags: list[str],
    tag_mode: TagMode = "any",
    exclude_tags: list[str] | None = None,
) -> Any | None:
    """Construit un filtre `extra_or_filters` (forme brute attendue par
    `DataHubGraph.get_urns_by_filter`) à partir des options CLI. Fonction pure
    (REQ-004) : aucune dépendance à `ReadContext` ni au réseau, donc testable
    isolément — voir tests/unit/test_selection.py.

    Renvoie None si aucun critère n'est fourni (le cas "tout le catalogue" ne
    doit pas produire un filtre vide, qui matcherait tout mais coûterait un
    aller-retour de recherche inutile — get_urns_by_filter s'en passe très
    bien via son seul entity_types)."""

    if tag_mode not in ("any", "all"):
        raise ValueError(f"tag_mode invalide : {tag_mode!r} (attendu 'any' ou 'all')")

    exclude_tags = exclude_tags or []
    if not domains and not tags and not exclude_tags:
        return None

    # Import différé : FilterDsl dépend de pydantic v2 côté acryl-datahub,
    # inutile de le charger pour un export qui ne filtre pas (même raison que
    # reader/graph.py::_load_property_definitions pour StructuredProperties).
    from datahub.sdk.search_filters import FilterDsl as F

    # Classes de filtre hétérogènes (_DomainFilter / _TagFilter / _Not, privées
    # côté acryl-datahub) : on ne les manipule qu'à travers .compile()/.to_raw().
    clauses: list[Any] = []

    if domains:
        clauses.append(F.domain([normalize_domain(d) for d in domains]))

    if tags:
        tag_urns = [normalize_tag(t) for t in tags]
        if tag_mode == "any":
            clauses.append(F.tag(tag_urns))
        else:  # "all"
            clauses.extend(F.tag([t]) for t in tag_urns)

    if exclude_tags:
        clauses.append(F.not_(F.tag([normalize_tag(t) for t in exclude_tags])))

    combined = clauses[0] if len(clauses) == 1 else F.and_(*clauses)
    return [{"and": [rule.to_raw() for rule in group["and"]]} for group in combined.compile()]


def select_data_product_urns(
    ctx: ReadContext,
    *,
    urns: list[str],
    domains: list[str],
    tags: list[str],
    tag_mode: TagMode = "any",
    exclude_tags: list[str] | None = None,
    on_warning: Callable[[str], None] | None = None,
) -> list[str]:
    exclude_tags = exclude_tags or []

    if urns:
        if (domains or tags or exclude_tags) and on_warning is not None:
            on_warning(_URN_PRECEDENCE_WARNING)
        return urns

    search_filter = build_selection_filter(
        domains=domains, tags=tags, tag_mode=tag_mode, exclude_tags=exclude_tags
    )
    return list(
        ctx.graph.get_urns_by_filter(entity_types=["dataProduct"], extra_or_filters=search_filter)
    )
