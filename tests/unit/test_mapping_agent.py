"""mapping/agent.py : branches "champ obligatoire absent" (`_missing`) pour
publisher/creator/hdab/contactPoint, et les champs optionnels de
`add_period_of_time` (end_date, note) — jusqu'ici jamais exercés isolément
par la suite (issue #79). `test_mapping_dataset.py` ne construit que des
`Agent`/`ContactPoint`/`PeriodOfTime` entièrement renseignés."""

from __future__ import annotations

from datetime import date

from rdflib import RDF, XSD, Graph, Literal, URIRef
from rdflib.namespace import RDFS

from dh_healthdcat.mapping.agent import (
    add_contact_point,
    add_creator,
    add_hdab,
    add_period_of_time,
    add_publisher,
)
from dh_healthdcat.mapping.namespaces import DCAT, DCT, FOAF, HEALTHDCATAP, VCARD
from dh_healthdcat.model import Agent, ContactPoint, PeriodOfTime, Severity, ValidationIssue

DATASET_URI = URIRef("urn:test:dataset")
DATASET_URN = "urn:li:dataProduct:test"
DATASET_NAME = "Jeu de test"


def _rdf_properties(issues: list[ValidationIssue]) -> set[str]:
    return {i.rdf_property for i in issues}


def test_add_publisher_reports_missing_type_note_and_trust_flag():
    agent = Agent(name="Editeur", homepage="https://x.test", mbox="e@x.test")
    issues: list[ValidationIssue] = []
    graph = Graph()

    node = add_publisher(graph, DATASET_URI, agent, DATASET_URN, DATASET_NAME, issues)

    assert _rdf_properties(issues) == {
        "healthdcatap:publisherType",
        "healthdcatap:publisherNote",
        "healthdcatap:trustedDataHolder",
    }
    assert all(i.severity is Severity.ERROR for i in issues)
    assert (node, HEALTHDCATAP.publisherType, None) not in graph
    assert (node, HEALTHDCATAP.trustedDataHolder, None) not in graph


def test_add_publisher_fully_filled_reports_nothing():
    agent = Agent(
        name="Editeur",
        homepage="https://x.test",
        mbox="e@x.test",
        publisher_type="https://x.test/vocab/hospital",
        publisher_note="Note publisher",
        trusted_data_holder=True,
    )
    issues: list[ValidationIssue] = []
    graph = Graph()

    node = add_publisher(graph, DATASET_URI, agent, DATASET_URN, DATASET_NAME, issues)

    assert issues == []
    assert (node, HEALTHDCATAP.publisherType, URIRef(agent.publisher_type)) in graph
    assert (node, HEALTHDCATAP.publisherNote, Literal("Note publisher", lang="fr")) in graph
    assert (node, HEALTHDCATAP.trustedDataHolder, Literal(True, datatype=XSD.boolean)) in graph


def test_add_creator_does_not_require_contact_fields():
    agent = Agent(name="Créateur", homepage="", mbox="")
    issues: list[ValidationIssue] = []
    graph = Graph()

    node = add_creator(graph, DATASET_URI, agent, DATASET_URN, DATASET_NAME, issues)

    assert (DATASET_URI, DCT.creator, node) in graph
    assert (node, RDF.type, FOAF.Agent) in graph
    assert issues == []  # homepage/mbox absents mais require_contact=False


def test_add_creator_still_reports_a_missing_name():
    agent = Agent(name="", homepage="https://x.test", mbox="e@x.test")
    issues: list[ValidationIssue] = []

    add_creator(Graph(), DATASET_URI, agent, DATASET_URN, DATASET_NAME, issues)

    assert _rdf_properties(issues) == {"foaf:name"}


def test_add_hdab_reports_missing_homepage_and_mbox():
    agent = Agent(name="HDAB", homepage="", mbox="")
    issues: list[ValidationIssue] = []

    add_hdab(Graph(), DATASET_URI, agent, DATASET_URN, DATASET_NAME, issues)

    assert _rdf_properties(issues) == {"foaf:homepage", "foaf:mbox"}


def test_add_contact_point_reports_missing_url():
    cp = ContactPoint(name="Contact", email="c@x.test", url=None)
    issues: list[ValidationIssue] = []
    graph = Graph()

    node = add_contact_point(graph, DATASET_URI, cp, DATASET_URN, DATASET_NAME, issues)

    assert _rdf_properties(issues) == {"vcard:hasURL"}
    assert (node, VCARD.hasURL, None) not in graph


def test_add_contact_point_with_url_reports_nothing():
    cp = ContactPoint(name="Contact", email="c@x.test", url="https://x.test/contact")
    issues: list[ValidationIssue] = []
    graph = Graph()

    node = add_contact_point(graph, DATASET_URI, cp, DATASET_URN, DATASET_NAME, issues)

    assert issues == []
    assert (node, VCARD.hasURL, URIRef("https://x.test/contact")) in graph
    assert (node, VCARD.hasEmail, URIRef("mailto:c@x.test")) in graph


def test_add_period_of_time_with_end_date_and_note():
    graph = Graph()
    period = PeriodOfTime(
        start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), note="Durée légale"
    )

    node = add_period_of_time(graph, DATASET_URI, DCT.temporal, period, "seed-1")

    assert (node, RDF.type, DCT.PeriodOfTime) in graph
    assert (node, DCAT.startDate, Literal(date(2024, 1, 1), datatype=XSD.date)) in graph
    assert (node, DCAT.endDate, Literal(date(2024, 12, 31), datatype=XSD.date)) in graph
    assert (node, RDFS.comment, Literal("Durée légale", lang="fr")) in graph
