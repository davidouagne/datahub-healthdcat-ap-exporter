"""foaf:Agent / vcard:Kind / dct:PeriodOfTime → triples RDF.

Contraintes SHACL suivies (shapes/ehds/hdap-validator-sensitivity-shape.ttl) :

- `:Agent_Shape` (tout foaf:Agent) : foaf:name ≥1 littéral.
- `:HealthAgent_Shape` (healthdcatap:hdab) : + foaf:homepage =1 IRI, foaf:mbox =1 IRI.
- `:HealthPublisherAgent_Shape` (dct:publisher) : + healthdcatap:publisherType =1,
  healthdcatap:publisherNote ≥1 littéral, healthdcatap:trustedDataHolder =1 xsd:boolean.
- `:Kind_Shape` (tout vcard:Kind, dcat:contactPoint) : vcard:hasURL ≥1 IRI,
  vcard:hasEmail ≥1 IRI (forme `<mailto:...>`, pas un littéral).
- `:PeriodOfTime_Shape` : dcat:startDate / dcat:endDate ≤1, typés date/dateTime.

`dct:creator` n'a, lui, aucune contrainte HealthDCAT-AP spécifique au-delà de
`:Agent_Shape` — on lui applique néanmoins les mêmes triples de base (nom,
homepage, mbox) par cohérence, sans exiger les champs propres au publisher.

Chaque fonction `add_*` accumule dans `issues` (en place) une `ValidationIssue`
de sévérité ERROR pour tout champ obligatoire absent, avec le nom de la
propriété DataHub à corriger — c'est le mécanisme derrière G4/P0-6.
"""

from __future__ import annotations

from rdflib import RDF, XSD, Graph, Literal, URIRef
from rdflib.namespace import RDFS

from dh_healthdcat.mapping.namespaces import DCAT, DCT, FOAF, HEALTHDCATAP, VCARD
from dh_healthdcat.mapping.nodes import node_uri
from dh_healthdcat.model import (
    Agent,
    ContactPoint,
    PeriodOfTime,
    Severity,
    ValidationIssue,
)


def _missing(
    issues: list[ValidationIssue],
    dataset_name: str,
    dataset_urn: str,
    rdf_property: str,
    datahub_field: str,
) -> None:
    issues.append(
        ValidationIssue(
            severity=Severity.ERROR,
            dataset_name=dataset_name,
            dataset_urn=dataset_urn,
            rdf_property=rdf_property,
            datahub_field=datahub_field,
            message="manquant",
        )
    )


def add_publisher(
    graph: Graph,
    dataset_uri: URIRef,
    agent: Agent,
    dataset_urn: str,
    dataset_name: str,
    issues: list[ValidationIssue],
) -> URIRef:
    """dct:publisher → :HealthPublisherAgent_Shape. Retourne le nœud créé."""

    node = node_uri("publisher", dataset_urn)
    graph.add((dataset_uri, DCT.publisher, node))
    _add_base_agent(graph, node, agent, dataset_urn, dataset_name, issues, role="publisher")

    if agent.publisher_type:
        graph.add((node, HEALTHDCATAP.publisherType, URIRef(agent.publisher_type)))
    else:
        _missing(
            issues,
            dataset_name,
            dataset_urn,
            "healthdcatap:publisherType",
            "fr.aphp.healthdcat.publisherType (CorpGroup)",
        )

    if agent.publisher_note:
        graph.add((node, HEALTHDCATAP.publisherNote, Literal(agent.publisher_note, lang="fr")))
    else:
        _missing(
            issues,
            dataset_name,
            dataset_urn,
            "healthdcatap:publisherNote",
            "fr.aphp.healthdcat.publisherNote (CorpGroup)",
        )

    if agent.trusted_data_holder is not None:
        graph.add(
            (
                node,
                HEALTHDCATAP.trustedDataHolder,
                Literal(agent.trusted_data_holder, datatype=XSD.boolean),
            )
        )
    else:
        _missing(
            issues,
            dataset_name,
            dataset_urn,
            "healthdcatap:trustedDataHolder",
            "fr.aphp.healthdcat.trustedDataHolder (CorpGroup)",
        )

    return node


def add_creator(
    graph: Graph,
    dataset_uri: URIRef,
    agent: Agent,
    dataset_urn: str,
    dataset_name: str,
    issues: list[ValidationIssue],
) -> URIRef:
    """dct:creator → foaf:Agent (:Agent_Shape uniquement, pas de contrainte santé)."""

    node = node_uri("creator", dataset_urn)
    graph.add((dataset_uri, DCT.creator, node))
    _add_base_agent(
        graph, node, agent, dataset_urn, dataset_name, issues, role="creator", require_contact=False
    )
    return node


def add_hdab(
    graph: Graph,
    dataset_uri: URIRef,
    agent: Agent,
    dataset_urn: str,
    dataset_name: str,
    issues: list[ValidationIssue],
) -> URIRef:
    """healthdcatap:hdab → :HealthAgent_Shape (homepage et mbox obligatoires)."""

    node = node_uri("hdab", dataset_urn)
    graph.add((dataset_uri, HEALTHDCATAP.hdab, node))
    _add_base_agent(graph, node, agent, dataset_urn, dataset_name, issues, role="hdab")
    return node


def _add_base_agent(
    graph: Graph,
    node: URIRef,
    agent: Agent,
    dataset_urn: str,
    dataset_name: str,
    issues: list[ValidationIssue],
    *,
    role: str,
    require_contact: bool = True,
) -> None:
    graph.add((node, RDF.type, FOAF.Agent))
    if agent.name:
        graph.add((node, FOAF.name, Literal(agent.name)))
    else:
        _missing(
            issues, dataset_name, dataset_urn, "foaf:name", f"owner ({role}) sans CorpGroup name"
        )

    if agent.homepage:
        graph.add((node, FOAF.homepage, URIRef(agent.homepage)))
    elif require_contact:
        _missing(
            issues,
            dataset_name,
            dataset_urn,
            "foaf:homepage",
            f"fr.aphp.healthdcat.agentHomepage (CorpGroup {role})",
        )

    if agent.mbox:
        graph.add((node, FOAF.mbox, URIRef(f"mailto:{agent.mbox}")))
    elif require_contact:
        _missing(
            issues,
            dataset_name,
            dataset_urn,
            "foaf:mbox",
            f"fr.aphp.healthdcat.agentEmail (CorpGroup {role})",
        )


def add_contact_point(
    graph: Graph,
    dataset_uri: URIRef,
    cp: ContactPoint,
    dataset_urn: str,
    dataset_name: str,
    issues: list[ValidationIssue],
) -> URIRef:
    """dcat:contactPoint → vcard:Kind (:Kind_Shape : hasURL et hasEmail obligatoires, en IRI)."""

    node = node_uri("contact", dataset_urn)
    graph.add((dataset_uri, DCAT.contactPoint, node))
    graph.add((node, RDF.type, VCARD.Kind))
    graph.add((node, VCARD.fn, Literal(cp.name)))
    graph.add((node, VCARD.hasEmail, URIRef(f"mailto:{cp.email}")))
    if cp.url:
        graph.add((node, VCARD.hasURL, URIRef(cp.url)))
    else:
        _missing(
            issues, dataset_name, dataset_urn, "vcard:hasURL", "fr.aphp.healthdcat.contactPointUrl"
        )
    return node


def add_period_of_time(
    graph: Graph, subject: URIRef, predicate: URIRef, period: PeriodOfTime, seed: str
) -> URIRef:
    """dct:temporal / healthdcatap:retentionPeriod → dct:PeriodOfTime."""

    node = node_uri("periodOfTime", seed)
    graph.add((subject, predicate, node))
    graph.add((node, RDF.type, DCT.PeriodOfTime))
    if period.start_date:
        graph.add((node, DCAT.startDate, Literal(period.start_date, datatype=XSD.date)))
    if period.end_date:
        graph.add((node, DCAT.endDate, Literal(period.end_date, datatype=XSD.date)))
    if period.note:
        graph.add((node, RDFS.comment, Literal(period.note, lang="fr")))
    return node
