"""Sélection des DataProducts à traiter — partagée par `export-file` et
`push-hdh` (cli.py) pour que les deux commandes filtrent (--urn/--domain/--tag)
de façon identique.

Voir spec/spec-feature-tag-filtering.md : le filtre est évalué côté serveur
(une seule requête `get_urns_by_filter`), pas en énumérant tout le catalogue
puis en testant chaque DataProduct un par un (coût en O(N) du v0, corrigé
ici) — d'où la séparation entre `build_selection_query` (pure, testable hors
ligne) et `select_data_product_urns` (l'appel réseau, délégué à `ReadContext`).

Ce module n'importe rien de `datahub.*` : la sélection s'exprime en termes
neutres (`DataProductQuery`), traduits en filtre DataHub derrière la
frontière `reader/graph.py` (ADR-0004 §4)."""

from __future__ import annotations

from collections.abc import Callable

from dh_healthdcat.reader.graph import DataProductQuery, ReadContext, TagMode

__all__ = [
    "TagMode",
    "build_selection_query",
    "normalize_domain",
    "normalize_tag",
    "select_data_product_urns",
]

_URN_PRECEDENCE_WARNING = (
    "--urn a été fourni : --domain/--tag/--exclude-tag sont ignorés "
    "(--urn est prioritaire, voir spec/spec-feature-tag-filtering.md)."
)


def normalize_domain(value: str) -> str:
    return value if value.startswith("urn:li:domain:") else f"urn:li:domain:{value}"


def normalize_tag(value: str) -> str:
    return value if value.startswith("urn:li:tag:") else f"urn:li:tag:{value}"


def build_selection_query(
    *,
    domains: list[str],
    tags: list[str],
    tag_mode: TagMode = "any",
    exclude_tags: list[str] | None = None,
) -> DataProductQuery:
    """Traduit les options CLI en `DataProductQuery` neutre : valide
    `tag_mode` et normalise noms courts → URN. Fonction pure (REQ-004),
    testable isolément — la traduction en filtre DataHub relève de
    `reader/graph.py::to_datahub_filter`, seule frontière avec DataHub."""

    if tag_mode not in ("any", "all"):
        raise ValueError(f"tag_mode invalide : {tag_mode!r} (attendu 'any' ou 'all')")

    return DataProductQuery(
        domains=tuple(normalize_domain(d) for d in domains),
        tags=tuple(normalize_tag(t) for t in tags),
        tag_mode=tag_mode,
        exclude_tags=tuple(normalize_tag(t) for t in exclude_tags or []),
    )


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

    query = build_selection_query(
        domains=domains, tags=tags, tag_mode=tag_mode, exclude_tags=exclude_tags
    )
    return ctx.find_data_product_urns(query)
