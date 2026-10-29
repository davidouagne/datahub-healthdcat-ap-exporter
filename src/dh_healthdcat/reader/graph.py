"""Contexte de lecture DataHub : connexion + caches.

`ReadContext` porte tout ce que le reader interroge à répétition pendant un
export :

- `get_entity(urn)` mémoïse `DataHubGraph.get_entity_semityped()`, limité aux
  aspects que le reader lit (`ASPECTS_READ`) — un export
  déréférence les mêmes domaines/glossaryTerms/owners des centaines de fois
  (P0-1).
- `property_definitions` résout une seule fois, au démarrage, toutes les
  définitions de structured properties via `StructuredProperties.list()`,
  indexées par `qualified_name` (P0-2).
- `get_dataset_profile(urn)` mémoïse `DataHubGraph.get_latest_timeseries_value()`
  pour l'aspect `datasetProfile` (timeseries, donc absent de
  `get_entity_semityped()` — voir sa docstring côté acryl-datahub), seule
  source de `dcat:byteSize`.
- `find_data_product_urns(query)` traduit une `DataProductQuery` neutre en
  filtre de recherche DataHub (`to_datahub_filter`) et l'évalue côté serveur.

Volontairement découplé de `acryl-datahub` au-delà de cette frontière : le
reste du code ne connaît que `ReadContext` et `DataProductQuery`, ce qui permet
de le tester avec un double (voir tests/fixtures/) sans instance DataHub ni
réseau, et cantonne ici toute adaptation entre versions DataHub (ADR-0004 §4).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

TagMode = Literal["any", "all"]


class SemitypedEntity(Protocol):
    """Ce que `DataHubGraph.get_entity_semityped()` retourne : un mapping
    aspect_name -> objet d'aspect typé (ou None/absent si l'entité n'a pas
    cet aspect). `AspectBag` côté acryl-datahub s'y conforme structurellement
    (l'accès positionnel évite de comparer le nom du 1ᵉʳ paramètre à `key`)."""

    def get(self, name: str, default: Any = None, /) -> Any: ...


class GraphLike(Protocol):
    """Sous-ensemble de `DataHubGraph` dont le reader dépend. N'importe quel
    objet respectant cette interface (y compris un double de test) convient."""

    def get_entity_semityped(
        self, entity_urn: str, aspects: list[str] | None = None
    ) -> SemitypedEntity: ...

    def get_urns_by_filter(
        self,
        *,
        entity_types: Sequence[str] | None = None,
        extra_or_filters: Any = None,
    ) -> Iterable[str]: ...

    def get_latest_timeseries_value(
        self, entity_urn: str, aspect_type: Any, filter_criteria_map: dict[str, str]
    ) -> Any: ...


@dataclass(slots=True)
class PropertyDefinition:
    qualified_name: str
    urn: str
    value_type: str  # ex. "urn:li:dataType:datahub.string"
    cardinality: str  # "SINGLE" | "MULTIPLE"
    entity_types: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DataProductQuery:
    """Critères de sélection des DataProducts, en termes neutres : URN déjà
    normalisées (`urn:li:domain:…`, `urn:li:tag:…`), aucune notion de filtre
    DataHub. Domaines en OU ; tags en OU (`any`) ou en ET (`all`) ; les tags
    exclus écartent tout DataProduct qui en porte un ; les trois groupes se
    combinent en ET."""

    domains: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    tag_mode: TagMode = "any"
    exclude_tags: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.domains or self.tags or self.exclude_tags)


def to_datahub_filter(query: DataProductQuery) -> list[dict[str, Any]] | None:
    """`extra_or_filters` (forme brute attendue par
    `DataHubGraph.get_urns_by_filter`) équivalent à `query`, ou None pour une
    requête vide — tout le catalogue, sans aller-retour de recherche inutile.

    Seul point du code qui manipule `FilterDsl`, la zone la plus fragile d'une
    version d'acryl-datahub à l'autre (classes privées `_DomainFilter` /
    `_TagFilter` / `_Not`, utilisées uniquement via `.compile()`/`.to_raw()`)."""

    if query.is_empty:
        return None

    # Import différé : FilterDsl dépend de pydantic v2 côté acryl-datahub,
    # inutile de le charger pour un export qui ne filtre pas (même raison que
    # `_load_property_definitions` pour StructuredProperties).
    from datahub.sdk.search_filters import FilterDsl as F

    clauses: list[Any] = []
    if query.domains:
        clauses.append(F.domain(list(query.domains)))
    if query.tags:
        if query.tag_mode == "any":
            clauses.append(F.tag(list(query.tags)))
        else:  # "all"
            clauses.extend(F.tag([t]) for t in query.tags)
    if query.exclude_tags:
        clauses.append(F.not_(F.tag(list(query.exclude_tags))))

    combined = clauses[0] if len(clauses) == 1 else F.and_(*clauses)
    return [{"and": [rule.to_raw() for rule in group["and"]]} for group in combined.compile()]


# Aspects demandés à DataHub, par type d'entité : exactement ceux que le reader
# lit (`entity.get(...)`). Seule liste à tenir à jour quand le reader lit un
# nouvel aspect — le double de test ne renvoie que les aspects demandés, donc
# un oubli ici fait échouer les tests. Demander une liste explicite plutôt que
# tous les aspects évite qu'un aspect ajouté par une version serveur plus
# récente, inconnu du client installé, soit téléchargé puis journalisé
# (`Ignoring unknown aspect type …`) à chaque entité lue (#142).
ASPECTS_READ: dict[str, tuple[str, ...]] = {
    "dataProduct": (
        "dataProductProperties",
        "structuredProperties",
        "globalTags",
        "glossaryTerms",
        "institutionalMemory",
    ),
    "dataset": (
        "datasetProperties",
        "editableDatasetProperties",
        "schemaMetadata",
        "deprecation",
        "globalTags",
        "structuredProperties",
    ),
    "glossaryTerm": ("glossaryTermInfo",),
}


def _entity_type(urn: str) -> str:
    """`urn:li:<type>:…` → `<type>`."""

    prefix, sep, rest = urn.partition("urn:li:")
    entity_type, colon, _ = rest.partition(":")
    if prefix or not sep or not entity_type or not colon:
        raise ValueError(f"URN DataHub invalide : {urn!r}")
    return entity_type


_PROFILE_CACHE_MISS = object()


@dataclass(slots=True)
class ReadContext:
    graph: GraphLike
    _entity_cache: dict[str, SemitypedEntity] = field(default_factory=dict)
    _property_definitions: dict[str, PropertyDefinition] | None = field(default=None, repr=False)
    _profile_cache: dict[str, Any] = field(default_factory=dict, repr=False)

    def get_entity(self, urn: str) -> SemitypedEntity:
        """Aspects `ASPECTS_READ` de l'entité, mémoïsés par URN. Une liste par
        type d'entité : le cache ne peut donc pas servir à un appelant une
        entité lue avec d'autres aspects que ceux qu'il attend."""

        cached = self._entity_cache.get(urn)
        if cached is None:
            entity_type = _entity_type(urn)
            aspects = ASPECTS_READ.get(entity_type)
            if aspects is None:
                raise ValueError(
                    f"type d'entité {entity_type!r} absent de ASPECTS_READ "
                    "(reader/graph.py) : déclarer les aspects lus"
                )
            cached = self.graph.get_entity_semityped(urn, aspects=list(aspects))
            self._entity_cache[urn] = cached
        return cached

    def get_dataset_profile(self, dataset_urn: str) -> Any:
        """Dernier `datasetProfile` (timeseries) d'un Dataset, ou None.

        Mémoïsé séparément de `get_entity` : `datasetProfile` n'apparaît
        jamais dans `get_entity_semityped()` (c'est un aspect timeseries —
        appeler `get_aspect` dessus lève `TypeError` côté acryl-datahub), il
        se lit via un endpoint distinct.
        """

        cached = self._profile_cache.get(dataset_urn, _PROFILE_CACHE_MISS)
        if cached is not _PROFILE_CACHE_MISS:
            return cached

        from datahub.metadata.schema_classes import DatasetProfileClass

        profile = self.graph.get_latest_timeseries_value(dataset_urn, DatasetProfileClass, {})
        self._profile_cache[dataset_urn] = profile
        return profile

    def find_data_product_urns(self, query: DataProductQuery) -> list[str]:
        """URN des DataProducts satisfaisant `query`, en une seule requête de
        recherche évaluée côté serveur (pas d'énumération + test un par un)."""

        return list(
            self.graph.get_urns_by_filter(
                entity_types=["dataProduct"], extra_or_filters=to_datahub_filter(query)
            )
        )

    @property
    def property_definitions(self) -> dict[str, PropertyDefinition]:
        if self._property_definitions is None:
            self._property_definitions = self._load_property_definitions()
        return self._property_definitions

    def _load_property_definitions(self) -> dict[str, PropertyDefinition]:
        # Import différé : StructuredProperties dépend de pydantic v2 côté
        # acryl-datahub, pas la peine de le charger si on ne fait que du mapping.
        from datahub.api.entities.structuredproperties.structuredproperties import (
            StructuredProperties,
        )

        definitions: dict[str, PropertyDefinition] = {}
        for prop in StructuredProperties.list(self.graph):  # type: ignore[arg-type]
            qualified_name = prop.qualified_name
            urn = prop.urn
            if qualified_name is None or urn is None:
                continue
            definitions[qualified_name] = PropertyDefinition(
                qualified_name=qualified_name,
                urn=urn,
                value_type=prop.type,
                cardinality=prop.cardinality or "SINGLE",
                entity_types=tuple(prop.entity_types or ()),
            )
        return definitions


def from_env() -> ReadContext:
    """Connexion GMS via les variables d'environnement / `~/.datahubenv`
    (mêmes conventions que la CLI `datahub`)."""

    from datahub.ingestion.graph.client import DataHubGraph, get_default_graph

    graph: DataHubGraph = get_default_graph()
    # DataHubGraph respecte GraphLike structurellement ; mypy ne reconnaît pas
    # `AspectBag` comme sous-type de `SemitypedEntity` (protocole minimal maison).
    return ReadContext(graph=graph)  # type: ignore[arg-type]


def from_config(server: str, token: str | None = None) -> ReadContext:
    from datahub.ingestion.graph.client import DataHubGraph
    from datahub.ingestion.graph.config import DatahubClientConfig

    graph = DataHubGraph(DatahubClientConfig(server=server, token=token))
    return ReadContext(graph=graph)  # type: ignore[arg-type]
