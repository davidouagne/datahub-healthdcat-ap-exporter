"""Modèle pivot entre la lecture DataHub (``reader/``) et la traduction RDF (``mapping/``).

Ces dataclasses ne connaissent ni DataHub ni RDF : elles portent uniquement les
valeurs déjà résolues (URIs de vocabulaire contrôlé incluses). C'est ce qui les
rend testables sans instance DataHub et sans réseau (voir tests/fixtures/).

Toute valeur `Optional` correspond à un champ HealthDCAT-AP non obligatoire ou
non renseigné dans DataHub — c'est au mapping de décider si son absence est
tolérable (cf. shapes/ehds/hdap-validator-sensitivity-shape.ttl) et de le
signaler via `ValidationIssue`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


@dataclass(frozen=True, slots=True)
class PeriodOfTime:
    """dct:PeriodOfTime — dcat:startDate / dcat:endDate."""

    start_date: date | None = None
    end_date: date | None = None
    note: str | None = None  # rdfs:comment, ex. healthdcatap:retentionPeriod


@dataclass(frozen=True, slots=True)
class ContactPoint:
    """dcat:contactPoint — vcard:Kind."""

    name: str
    email: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class Agent:
    """foaf:Agent — sert pour dct:publisher, dct:creator et healthdcatap:hdab.

    Les champs `publisher_type` / `publisher_note` / `trusted_data_holder` ne
    s'appliquent qu'au rôle `dct:publisher` (:HealthPublisherAgent_Shape) ;
    `country` ne s'applique qu'au rôle `healthdcatap:hdab` (adresse locn:).
    Le mapping les ignore silencieusement pour les autres rôles.
    """

    name: str
    homepage: str
    mbox: str  # adresse e-mail, sans le préfixe "mailto:"
    publisher_type: str | None = None  # URI d'autorité
    publisher_note: str | None = None
    trusted_data_holder: bool | None = None
    country: str | None = None  # URI NUTS/pays, pour healthdcatap:hdab


@dataclass(frozen=True, slots=True)
class Column:
    """csvw:Column."""

    name: str
    description: str | None
    datatype: str  # ex. "string", "integer" — vocabulaire csvw
    is_primary_key: bool = False


@dataclass(frozen=True, slots=True)
class Table:
    """csvw:Table — schéma d'une distribution."""

    title: str
    columns: tuple[Column, ...] = ()


@dataclass(frozen=True, slots=True)
class Distribution:
    """dcat:Distribution ou adms:sample selon `is_sample`.

    Le SHACL HDH exige, pour une distribution (pas un sample) :
    dcat:byteSize (=1, nonNegativeInteger), dct:format (=1), dct:rights (=1),
    dcatap:applicableLegislation (≥1) — voir :healthDistribution_Shape.
    Ces exigences supplémentaires ne s'appliquent PAS aux adms:sample.
    """

    node_id: str  # UUID stable pour <distribution:{id}> / <sample:{id}>
    title: str
    is_sample: bool
    description: str | None = None
    access_url: str | None = None
    download_url: str | None = None
    format_uri: str | None = None
    media_type_uri: str | None = None
    byte_size: int | None = None
    rights: str | None = None
    status_uri: str | None = None
    issued: datetime | None = None
    modified: datetime | None = None
    applicable_legislation: tuple[str, ...] = ()
    table: Table | None = None
    source_urn: str = ""  # URN DataHub du Dataset source, pour les messages d'erreur


class Severity(str, Enum):
    ERROR = "error"  # propriété obligatoire manquante (SHACL sh:Violation)
    WARNING = "warning"  # coercition de type, vocabulaire inconnu, valeur douteuse


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Un problème détecté pendant la traduction, avant même l'appel à pyshacl.

    C'est ce qui alimente le rapport lisible exigé par G4 / P0-6 :
    « DataProduct "X" : healthdcatap:healthTheme manquant → renseigner
    fr.aphp.healthdcat.healthTheme ».
    """

    severity: Severity
    dataset_name: str
    dataset_urn: str
    rdf_property: str  # ex. "healthdcatap:healthTheme"
    datahub_field: str  # ex. "fr.aphp.healthdcat.healthTheme"
    message: str

    def __str__(self) -> str:  # pragma: no cover - formatage simple
        prefix = "ERREUR" if self.severity is Severity.ERROR else "avertissement"
        return (
            f'{prefix}: DataProduct "{self.dataset_name}" : {self.rdf_property} '
            f"{self.message} → renseigner {self.datahub_field}"
        )


@dataclass(slots=True)
class HealthDataset:
    """dcat:Dataset — la racine du graphe HealthDCAT-AP pour un DataProduct.

    `issues` accumule les `ValidationIssue` détectées pendant la lecture/traduction
    (champs obligatoires absents, coercitions douteuses). Le pivot reste
    intentionnellement permissif : c'est `validate/shacl.py` qui décide si le
    graphe final est exportable, `issues` ne fait qu'accélérer le diagnostic.
    """

    # Identité
    source_urn: str  # urn:li:dataProduct:...
    dataset_id: str  # DataProductKey.id, sert à construire dct:identifier
    identifier: str  # dct:identifier complet (xsd:anyURI)
    title: str
    description: str

    # Descriptif
    acronym: str | None = None
    keywords: tuple[str, ...] = ()
    theme: tuple[str, ...] = ()  # dcat:theme, URIs data-theme
    dataset_type: str | None = None  # dct:type, URI, cardinalité SHACL = 1
    access_rights: str | None = None  # dct:accessRights, URI, cardinalité SHACL = 1
    applicable_legislation: tuple[str, ...] = ()
    language: tuple[str, ...] = ()

    # Agents
    publisher: Agent | None = None
    creator: Agent | None = None
    contact_point: ContactPoint | None = None
    hdab: Agent | None = None

    # Contexte réglementaire / méthodologique
    provenance: str | None = None
    purpose: str | None = None
    legal_basis: tuple[str, ...] = ()
    personal_data: tuple[str, ...] = ()

    # Santé
    health_category: tuple[str, ...] = ()
    health_theme: tuple[str, ...] = ()
    spatial: tuple[str, ...] = ()
    number_of_records: int | None = None
    number_of_unique_individuals: int | None = None
    min_typical_age: int | None = None
    max_typical_age: int | None = None
    population_coverage: str | None = None
    retention_period: PeriodOfTime | None = None
    coding_system: tuple[str, ...] = ()

    # Temporel / cycle de vie
    issued: datetime | None = None
    modified: datetime | None = None
    temporal: PeriodOfTime | None = None
    accrual_periodicity: str | None = None

    # Divers
    conforms_to: tuple[str, ...] = ()
    license: str | None = None
    is_referenced_by: tuple[str, ...] = ()
    pages: tuple[str, ...] = ()

    # Distributions
    distributions: tuple[Distribution, ...] = ()  # dcat:distribution
    samples: tuple[Distribution, ...] = ()  # adms:sample

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity is Severity.ERROR for i in self.issues)
