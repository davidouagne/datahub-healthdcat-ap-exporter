"""Sélection des DataProducts à traiter — partagée par `export-file` et `push-hdh`
(cli.py) pour que les deux commandes filtrent (--urn/--domain/--tag) de façon
identique."""

from __future__ import annotations

from dh_healthdcat.reader.graph import ReadContext


def discover_urns(ctx: ReadContext, explicit_urns: list[str]) -> list[str]:
    if explicit_urns:
        return explicit_urns
    return list(ctx.graph.get_urns_by_filter(entity_types=["dataProduct"]))


def entity_has_any(ctx: ReadContext, urn: str, aspect_name: str, wanted: set[str]) -> bool:
    if not wanted:
        return True
    entity = ctx.get_entity(urn)
    aspect = entity.get(aspect_name)
    if aspect is None:
        return False
    if aspect_name == "domains":
        return any(d in wanted for d in aspect.domains)
    if aspect_name == "globalTags":
        return any(t.tag in wanted for t in aspect.tags)
    return False


def normalize_domain(value: str) -> str:
    return value if value.startswith("urn:li:domain:") else f"urn:li:domain:{value}"


def normalize_tag(value: str) -> str:
    return value if value.startswith("urn:li:tag:") else f"urn:li:tag:{value}"


def select_data_product_urns(
    ctx: ReadContext,
    *,
    urns: list[str],
    domains: list[str],
    tags: list[str],
) -> list[str]:
    domain_urns = {normalize_domain(d) for d in domains}
    tag_urns = {normalize_tag(t) for t in tags}
    candidates = discover_urns(ctx, urns)
    return [
        u
        for u in candidates
        if entity_has_any(ctx, u, "domains", domain_urns) and entity_has_any(ctx, u, "globalTags", tag_urns)
    ]
