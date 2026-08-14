"""Contexte de lecture DataHub : connexion + caches.

`ReadContext` porte tout ce que le reader interroge à répétition pendant un
export :

- `get_entity(urn)` mémoïse `DataHubGraph.get_entity_semityped()` — un export
  déréférence les mêmes domaines/glossaryTerms/owners des centaines de fois
  (P0-1).
- `property_definitions` résout une seule fois, au démarrage, toutes les
  définitions de structured properties via `StructuredProperties.list()`,
  indexées par `qualified_name` (P0-2).
- `get_dataset_profile(urn)` mémoïse `DataHubGraph.get_latest_timeseries_value()`
  pour l'aspect `datasetProfile` (timeseries, donc absent de
  `get_entity_semityped()` — voir sa docstring côté acryl-datahub), seule
  source de `dcat:byteSize`.

Volontairement découplé de `acryl-datahub` au-delà de cette frontière : le
reste du reader ne connaît que `ReadContext`, ce qui permet de le tester avec
un double (voir tests/fixtures/) sans instance DataHub ni réseau.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class SemitypedEntity(Protocol):
    """Ce que `DataHubGraph.get_entity_semityped()` retourne : un mapping
    aspect_name -> objet d'aspect typé (ou None/absent si l'entité n'a pas
    cet aspect)."""

    def get(self, aspect_name: str, default: Any = None) -> Any: ...


class GraphLike(Protocol):
    """Sous-ensemble de `DataHubGraph` dont le reader dépend. N'importe quel
    objet respectant cette interface (y compris un double de test) convient."""

    def get_entity_semityped(self, urn: str, aspects: list[str] | None = None) -> SemitypedEntity: ...

    def get_urns_by_filter(self, *, entity_types: list[str] | None = None, **kwargs: Any) -> Any: ...

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


_PROFILE_CACHE_MISS = object()


@dataclass(slots=True)
class ReadContext:
    graph: GraphLike
    _entity_cache: dict[str, SemitypedEntity] = field(default_factory=dict)
    _property_definitions: dict[str, PropertyDefinition] | None = field(default=None, repr=False)
    _profile_cache: dict[str, Any] = field(default_factory=dict, repr=False)

    def get_entity(self, urn: str) -> SemitypedEntity:
        cached = self._entity_cache.get(urn)
        if cached is None:
            cached = self.graph.get_entity_semityped(urn)
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
            definitions[prop.qualified_name] = PropertyDefinition(
                qualified_name=prop.qualified_name,
                urn=prop.urn,
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
    return ReadContext(graph=graph)


def from_config(server: str, token: str | None = None) -> ReadContext:
    from datahub.ingestion.graph.client import DataHubGraph
    from datahub.ingestion.graph.config import DatahubClientConfig

    graph = DataHubGraph(DatahubClientConfig(server=server, token=token))
    return ReadContext(graph=graph)
