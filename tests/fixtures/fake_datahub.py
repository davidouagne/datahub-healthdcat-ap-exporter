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
# URI de base de l'adoptant fictif (ADR-0005 §4 : jamais de valeur par défaut).
BASE_URI = "https://example.org"
ASSET_URN = "urn:li:dataset:(urn:li:dataPlatform:s3,sharing_layer_Patient.ndjson,PROD)"
SAMPLE_URN = "urn:li:dataset:(urn:li:dataPlatform:s3,sharing_layer_Patient_sample.ndjson,PROD)"

# Volontairement absente de assets.yml, pour vérifier la détection de dérive
# (reader/dataproduct.py::_warn_undeclared_properties).
UNDECLARED_PROPERTY = "healthdcatap.oldRemovedProperty"

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
                assets=[
                    NS(destinationUrn=ASSET_URN, outputPort=False),
                    NS(destinationUrn=SAMPLE_URN, outputPort=False),
                ],
                externalUrl=None,
            ),
            "ownership": NS(
                owners=[
                    NS(
                        owner="urn:li:corpuser:antoine.sansegundo",
                        typeUrn=None,
                        type="TECHNICAL_OWNER",
                    )
                ]
            ),
            "globalTags": NS(tags=[NS(tag="urn:li:tag:aphp:access")]),
            "glossaryTerms": NS(terms=[]),
            "domains": NS(domains=["urn:li:domain:9306fe49bb1f70f491a712ff19b8d972"]),
            "structuredProperties": NS(
                properties=[
                    _sp("healthdcatap.datasetType", "PERSONAL_DATA"),
                    _sp("healthdcatap.accessRights", "NON_PUBLIC"),
                    _sp(
                        "healthdcatap.applicableLegislation",
                        "COMMISSION IMPLEMENTING REGULATION (EU) 2023/138",
                    ),
                    _sp("healthdcatap.healthCategory", "HRAD"),
                    _sp("healthdcatap.healthTheme", "health_systems"),
                    _sp("healthdcatap.spatialCoverage", "FRA"),
                    _sp(
                        "healthdcatap.provenance",
                        "Donnees issues du dossier patient informatise ORBIS.",
                    ),
                    _sp(
                        "healthdcatap.purpose",
                        "Recherche et pilotage de l'activite hospitaliere.",
                    ),
                    _sp("healthdcatap.contactPointName", "Coordination EDS"),
                    _sp("healthdcatap.contactPointEmail", "eds-coord@aphp.fr"),
                    _sp("healthdcatap.contactPointUrl", "https://eds.aphp.fr"),
                    _sp("healthdcatap.license", "https://eds.aphp.fr/licence"),
                    # referenceSpecification : un code du vocab + un code local (OSIRIS)
                    _sp("healthdcatap.referenceSpecification", "HL7-FHIR-R4", "OSIRIS"),
                    # isReferencedBy : DOI nu, DOI préfixé "doi:", et URL complète
                    _sp(
                        "healthdcatap.isReferencedBy",
                        "10.1234/abcd.2019",
                        "doi:10.5555/xyz",
                        "https://hal.science/hal-04",
                    ),
                    _sp(
                        "healthdcatap.numberOfRecords", "1000000000"
                    ),  # string au lieu de number : coercition
                    _sp("healthdcatap.publishingFrequency", "DAILY"),
                    _sp(UNDECLARED_PROPERTY, "x"),
                    # Publisher (structured properties plates sur le DataProduct)
                    _sp(
                        "healthdcatap.publisherName",
                        "Assistance Publique - Hopitaux de Paris",
                    ),
                    _sp("healthdcatap.publisherHomepage", "https://www.aphp.fr"),
                    _sp("healthdcatap.publisherEmail", "eds-contact@aphp.fr"),
                    _sp("healthdcatap.publisherType", "Hospital or Healthcare System"),
                    _sp("healthdcatap.publisherNote", "EDS de l'AP-HP"),
                    _sp("healthdcatap.trustedDataHolder", "true"),
                    # HDAB
                    _sp("healthdcatap.hdabName", "Health Data Hub"),
                    _sp("healthdcatap.hdabHomepage", "https://health-data-hub.fr"),
                    _sp("healthdcatap.hdabEmail", "contact@health-data-hub.fr"),
                ]
            ),
        },
        ASSET_URN: {
            "datasetProperties": NS(
                name="Patient.ndjson",
                description="Ressources FHIR Patient",
                externalUrl=None,
                created=None,
                lastModified=None,
            ),
            "editableDatasetProperties": None,
            "schemaMetadata": NS(
                fields=[
                    NS(
                        fieldPath="id",
                        nativeDataType="string",
                        description="Identifiant",
                        isPartOfKey=True,
                    ),
                    NS(
                        fieldPath="gender",
                        nativeDataType="string",
                        description="Sexe",
                        isPartOfKey=False,
                    ),
                ]
            ),
            "deprecation": None,
            "globalTags": NS(tags=[]),
            "structuredProperties": NS(
                properties=[
                    _sp(
                        "healthdcatap.accessUrl",
                        "https://s3.aphp.fr/sharing-layer/Patient.ndjson",
                    ),
                    _sp("healthdcatap.distributionStatus", "COMPLETED"),
                ]
            ),
        },
        SAMPLE_URN: {
            "datasetProperties": NS(
                name="Patient_sample.ndjson",
                description="Echantillon FHIR Patient",
                externalUrl=None,
                created=None,
                lastModified=None,
            ),
            "editableDatasetProperties": None,
            "schemaMetadata": NS(fields=[]),
            "deprecation": None,
            "globalTags": NS(tags=[NS(tag="urn:li:tag:dcat:sample")]),
            "structuredProperties": NS(
                properties=[
                    _sp(
                        "healthdcatap.accessUrl",
                        "https://s3.aphp.fr/sharing-layer/Patient_sample.ndjson",
                    )
                ]
            ),
        },
        UNREADABLE_DATAPRODUCT_URN: {
            "dataProductProperties": None,
        },
        NONCONFORMING_DATAPRODUCT_URN: {
            "dataProductProperties": NS(
                name="DataProduct en cours de peuplement",
                description="Squelette sans propriétés HealthDCAT-AP renseignées.",
                assets=[],
                externalUrl=None,
            ),
        },
    }


# Profil (aspect timeseries datasetProfile) : renseigné uniquement pour
# ASSET_URN (la distribution), pas SAMPLE_URN — un adms:sample n'exige pas
# dcat:byteSize, inutile de lui en fournir un pour que les tests restent
# significatifs sur ce point.
_PROFILES = {ASSET_URN: NS(sizeInBytes=123456)}


class _RequestedAspects(dict):
    """Entité renvoyée par `FakeGraph` : lire un aspect non demandé lève, même
    si la fixture ne le porte pas — un oubli dans `ASPECTS_READ` est détecté
    dès que le reader *tente* la lecture, pas seulement quand la donnée
    existe."""

    def __init__(self, aspects: dict, requested: list[str]) -> None:
        super().__init__(aspects)
        self._requested = frozenset(requested)

    def get(self, name, default=None, /):
        assert name in self._requested, (
            f"aspect {name!r} lu sans avoir été demandé (ASPECTS_READ, reader/graph.py)"
        )
        return super().get(name, default)


class FakeGraph:
    """Substitut minimal de `DataHubGraph` : `get_entity_semityped` et
    `get_latest_timeseries_value` sont ce que `ReadContext` utilise.

    `get_entity_semityped_calls` et `last_extra_or_filters` instrumentent le
    double pour tests/unit/test_selection.py : ils permettent de prouver que
    `select_data_product_urns` ne fait plus d'appel par entité (N+1, voir
    docs/specs/feature-tag-filtering.md) et de vérifier quel filtre a
    effectivement été transmis à `get_urns_by_filter`."""

    def __init__(self) -> None:
        self._entities = _entities()
        self.get_entity_semityped_calls: list[str] = []
        self.requested_aspects: dict[str, list[str]] = {}
        # Réponse de /config ; une Exception simule un /config inaccessible.
        self.config: dict | Exception = {
            "versions": {"acryldata/datahub": {"version": "v1.7.0.1"}},
            "datahub": {"serverEnv": "core"},
        }
        self.last_extra_or_filters: object = None

    def get_entity_semityped(self, urn: str, aspects: list[str] | None = None) -> dict:
        """Comme DataHub, ne renvoie que les aspects demandés : un aspect lu
        par le reader mais absent de `ASPECTS_READ` est donc invisible ici et
        fait échouer les tests (#142)."""

        assert aspects, "ReadContext doit demander une liste d'aspects explicite"
        self.get_entity_semityped_calls.append(urn)
        self.requested_aspects[urn] = list(aspects)
        entity = self._entities[urn]
        return _RequestedAspects(
            {name: value for name, value in entity.items() if name in aspects}, aspects
        )

    def get_urns_by_filter(self, *, entity_types=None, extra_or_filters=None, **kwargs):
        self.last_extra_or_filters = extra_or_filters
        if entity_types == ["dataProduct"]:
            return list(ALL_DATAPRODUCT_URNS)
        return []

    def get_config(self) -> dict:
        if isinstance(self.config, Exception):
            raise self.config
        return self.config

    def get_latest_timeseries_value(self, entity_urn, aspect_type, filter_criteria_map):
        return _PROFILES.get(entity_urn)


# Sous-ensemble des définitions réellement déclarées dans assets.yml — UNDECLARED_PROPERTY
# est intentionnellement absente.
_DECLARED_QUALIFIED_NAMES = [
    "healthdcatap.datasetType",
    "healthdcatap.accessRights",
    "healthdcatap.applicableLegislation",
    "healthdcatap.healthCategory",
    "healthdcatap.healthTheme",
    "healthdcatap.spatialCoverage",
    "healthdcatap.provenance",
    "healthdcatap.purpose",
    "healthdcatap.contactPointName",
    "healthdcatap.contactPointEmail",
    "healthdcatap.contactPointUrl",
    "healthdcatap.license",
    "healthdcatap.numberOfRecords",
    "healthdcatap.publishingFrequency",
    "healthdcatap.accessUrl",
    "healthdcatap.referenceSpecification",
    "healthdcatap.isReferencedBy",
    "healthdcatap.distributionStatus",
    "healthdcatap.publisherName",
    "healthdcatap.publisherHomepage",
    "healthdcatap.publisherEmail",
    "healthdcatap.publisherType",
    "healthdcatap.publisherNote",
    "healthdcatap.trustedDataHolder",
    "healthdcatap.hdabName",
    "healthdcatap.hdabHomepage",
    "healthdcatap.hdabEmail",
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
