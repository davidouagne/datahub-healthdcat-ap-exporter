"""Double minimal de DataHub : un DataProduct entièrement renseigné, deux
assets (une distribution, un échantillon), publisher et HDAB portés par des
structured properties plates sur le DataProduct lui-même (pas de CorpGroup —
voir reader/agents.py pour pourquoi). Reproduit la forme exacte de
`get_entity_semityped()` avec des `SimpleNamespace` plutôt que les vraies
classes `acryl-datahub` — suffisant puisque le reader n'accède qu'à des
attributs, jamais au typage.

Sert de fixture partagée aux tests de `reader/` (tests/unit/test_reader_*.py).
Pas de réseau, pas d'instance DataHub : conforme à P0-1/G3 (le mapping doit
être testable hors ligne).
"""

from __future__ import annotations

from types import SimpleNamespace as NS

from dh_healthdcat.reader.graph import PropertyDefinition, ReadContext

DATAPRODUCT_URN = "urn:li:dataProduct:b78435bfad26dab4c11e6e41c2a72b53"
ASSET_URN = "urn:li:dataset:(urn:li:dataPlatform:s3,sharing_layer_Patient.ndjson,PROD)"
SAMPLE_URN = "urn:li:dataset:(urn:li:dataPlatform:s3,sharing_layer_Patient_sample.ndjson,PROD)"

# Volontairement absente de assets.yml, pour vérifier la détection de dérive
# (reader/dataproduct.py::_warn_undeclared_properties).
UNDECLARED_PROPERTY = "fr.aphp.healthdcat.oldRemovedProperty"

# Illisible : pas de dataProductProperties.name côté DataHub (DataProduct
# invalide ou introuvable, reader/dataproduct.py:114-115 lève ValueError).
# Sert à exercer l'outcome "Unreadable" du pipeline (spec-feature-export-pipeline.md).
UNREADABLE_DATAPRODUCT_URN = "urn:li:dataProduct:unreadable"

# Lisible mais non conforme SHACL : dataProductProperties minimal (nom +
# description), aucune structured property, aucun asset. dataset_to_graph()
# journalise une ERROR pour chaque champ obligatoire absent (dct:accessRights,
# dcatap:applicableLegislation, dcat:contactPoint, dcat:distribution...) et
# validate_graph() renvoie conforms=False. Sert à exercer l'outcome "Rejected".
NONCONFORMING_DATAPRODUCT_URN = "urn:li:dataProduct:nonconforming"

# Ordre : valide, illisible, non conforme — utilisé par FakeGraph.get_urns_by_filter
# pour une sélection non filtrée (mixte, les trois outcomes du pipeline).
ALL_DATAPRODUCT_URNS = [DATAPRODUCT_URN, UNREADABLE_DATAPRODUCT_URN, NONCONFORMING_DATAPRODUCT_URN]


def _sp(name: str, *values: str) -> NS:
    return NS(propertyUrn=f"urn:li:structuredProperty:{name}", values=list(values))


def _entities() -> dict[str, dict]:
    return {
        DATAPRODUCT_URN: {
            "dataProductProperties": NS(
                name="Venues et sejours des patients",
                description="Enregistrements de venues et sejours.",
                assets=[NS(destinationUrn=ASSET_URN), NS(destinationUrn=SAMPLE_URN)],
                lastModified=None,
            ),
            "ownership": NS(owners=[NS(owner="urn:li:corpuser:antoine.sansegundo", typeUrn=None, type="TECHNICAL_OWNER")]),
            "globalTags": NS(tags=[NS(tag="urn:li:tag:aphp:access")]),
            "glossaryTerms": NS(terms=[]),
            "domains": NS(domains=["urn:li:domain:9306fe49bb1f70f491a712ff19b8d972"]),
            "structuredProperties": NS(
                properties=[
                    _sp("fr.aphp.healthdcat.datasetType", "PERSONAL_DATA"),
                    _sp("fr.aphp.healthdcat.accessRights", "NON_PUBLIC"),
                    _sp("fr.aphp.healthdcat.applicableLegislation", "COMMISSION IMPLEMENTING REGULATION (EU) 2023/138"),
                    _sp("fr.aphp.healthdcat.healthCategory", "HRAD"),
                    _sp("fr.aphp.healthdcat.healthTheme", "health_systems"),
                    _sp("fr.aphp.healthdcat.spatialCoverage", "FRA"),
                    _sp("fr.aphp.healthdcat.provenance", "Donnees issues du dossier patient informatise ORBIS."),
                    _sp("fr.aphp.healthdcat.purpose", "Recherche et pilotage de l'activite hospitaliere."),
                    _sp("fr.aphp.healthdcat.contactPointName", "Coordination EDS"),
                    _sp("fr.aphp.healthdcat.contactPointEmail", "eds-coord@aphp.fr"),
                    _sp("fr.aphp.healthdcat.contactPointUrl", "https://eds.aphp.fr"),
                    _sp("fr.aphp.healthdcat.license", "https://eds.aphp.fr/licence"),
                    _sp("fr.aphp.healthdcat.numberOfRecords", "1000000000"),  # string au lieu de number : coercition
                    _sp("fr.aphp.healthdcat.publishingFrequency", "DAILY"),
                    _sp(UNDECLARED_PROPERTY, "x"),
                    # Publisher (structured properties plates sur le DataProduct)
                    _sp("fr.aphp.healthdcat.publisherName", "Assistance Publique - Hopitaux de Paris"),
                    _sp("fr.aphp.healthdcat.publisherHomepage", "https://www.aphp.fr"),
                    _sp("fr.aphp.healthdcat.publisherEmail", "eds-contact@aphp.fr"),
                    _sp("fr.aphp.healthdcat.publisherType", "Hospital or Healthcare System"),
                    _sp("fr.aphp.healthdcat.publisherNote", "EDS de l'AP-HP"),
                    _sp("fr.aphp.healthdcat.trustedDataHolder", "true"),
                    # HDAB
                    _sp("fr.aphp.healthdcat.hdabName", "Health Data Hub"),
                    _sp("fr.aphp.healthdcat.hdabHomepage", "https://health-data-hub.fr"),
                    _sp("fr.aphp.healthdcat.hdabEmail", "contact@health-data-hub.fr"),
                ]
            ),
        },
        ASSET_URN: {
            "datasetProperties": NS(name="Patient.ndjson", description="Ressources FHIR Patient", externalUrl=None, created=None, lastModified=None),
            "editableDatasetProperties": None,
            "schemaMetadata": NS(
                fields=[
                    NS(fieldPath="id", nativeDataType="string", description="Identifiant", isPartOfKey=True),
                    NS(fieldPath="gender", nativeDataType="string", description="Sexe", isPartOfKey=False),
                ]
            ),
            "deprecation": None,
            "globalTags": NS(tags=[]),
            "structuredProperties": NS(properties=[_sp("fr.aphp.healthdcat.accessUrl", "https://s3.aphp.fr/sharing-layer/Patient.ndjson")]),
        },
        SAMPLE_URN: {
            "datasetProperties": NS(name="Patient_sample.ndjson", description="Echantillon FHIR Patient", externalUrl=None, created=None, lastModified=None),
            "editableDatasetProperties": None,
            "schemaMetadata": NS(fields=[]),
            "deprecation": None,
            "globalTags": NS(tags=[NS(tag="urn:li:tag:dcat:sample")]),
            "structuredProperties": NS(properties=[_sp("fr.aphp.healthdcat.accessUrl", "https://s3.aphp.fr/sharing-layer/Patient_sample.ndjson")]),
        },
        UNREADABLE_DATAPRODUCT_URN: {
            "dataProductProperties": None,
        },
        NONCONFORMING_DATAPRODUCT_URN: {
            "dataProductProperties": NS(
                name="DataProduct en cours de peuplement",
                description="Squelette sans propriétés HealthDCAT-AP renseignées.",
                assets=[],
                lastModified=None,
            ),
        },
    }


# Profil (aspect timeseries datasetProfile) : renseigné uniquement pour
# ASSET_URN (la distribution), pas SAMPLE_URN — un adms:sample n'exige pas
# dcat:byteSize, inutile de lui en fournir un pour que les tests restent
# significatifs sur ce point.
_PROFILES = {ASSET_URN: NS(sizeInBytes=123456)}


class FakeGraph:
    """Substitut minimal de `DataHubGraph` : `get_entity_semityped` et
    `get_latest_timeseries_value` sont ce que `ReadContext` utilise.

    `get_entity_semityped_calls` et `last_extra_or_filters` instrumentent le
    double pour tests/unit/test_selection.py : ils permettent de prouver que
    `select_data_product_urns` ne fait plus d'appel par entité (N+1, voir
    spec/spec-feature-tag-filtering.md) et de vérifier quel filtre a
    effectivement été transmis à `get_urns_by_filter`."""

    def __init__(self) -> None:
        self._entities = _entities()
        self.get_entity_semityped_calls: list[str] = []
        self.last_extra_or_filters: object = None

    def get_entity_semityped(self, urn: str, aspects: list[str] | None = None) -> dict:
        self.get_entity_semityped_calls.append(urn)
        return self._entities[urn]

    def get_urns_by_filter(self, *, entity_types=None, extra_or_filters=None, **kwargs):  # noqa: ANN001, ANN003
        self.last_extra_or_filters = extra_or_filters
        if entity_types == ["dataProduct"]:
            return list(ALL_DATAPRODUCT_URNS)
        return []

    def get_latest_timeseries_value(self, entity_urn, aspect_type, filter_criteria_map):  # noqa: ANN001
        return _PROFILES.get(entity_urn)


# Sous-ensemble des définitions réellement déclarées dans assets.yml — UNDECLARED_PROPERTY
# est intentionnellement absente.
_DECLARED_QUALIFIED_NAMES = [
    "fr.aphp.healthdcat.datasetType", "fr.aphp.healthdcat.accessRights", "fr.aphp.healthdcat.applicableLegislation",
    "fr.aphp.healthdcat.healthCategory", "fr.aphp.healthdcat.healthTheme", "fr.aphp.healthdcat.spatialCoverage",
    "fr.aphp.healthdcat.provenance", "fr.aphp.healthdcat.purpose", "fr.aphp.healthdcat.contactPointName",
    "fr.aphp.healthdcat.contactPointEmail", "fr.aphp.healthdcat.contactPointUrl", "fr.aphp.healthdcat.license",
    "fr.aphp.healthdcat.numberOfRecords", "fr.aphp.healthdcat.publishingFrequency", "fr.aphp.healthdcat.accessUrl",
    "fr.aphp.healthdcat.publisherName", "fr.aphp.healthdcat.publisherHomepage", "fr.aphp.healthdcat.publisherEmail",
    "fr.aphp.healthdcat.publisherType", "fr.aphp.healthdcat.publisherNote", "fr.aphp.healthdcat.trustedDataHolder",
    "fr.aphp.healthdcat.hdabName", "fr.aphp.healthdcat.hdabHomepage", "fr.aphp.healthdcat.hdabEmail",
]


def build_context() -> ReadContext:
    ctx = ReadContext(graph=FakeGraph())
    # Court-circuite StructuredProperties.list() (appel réseau réel) :
    ctx._property_definitions = {
        name: PropertyDefinition(
            qualified_name=name,
            urn=f"urn:li:structuredProperty:{name}",
            value_type="urn:li:dataType:datahub.string",
            cardinality="SINGLE",
        )
        for name in _DECLARED_QUALIFIED_NAMES
    }
    return ctx
