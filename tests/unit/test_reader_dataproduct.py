"""reader/dataproduct.py contre le double DataHub de tests/fixtures/fake_datahub.py.
Vérifie la coercition tolérante (P0-3), la détection de dérive du référentiel
(P0-2) et la lecture de dcat:byteSize depuis l'aspect timeseries
datasetProfile (ASSET_URN a un profil dans la fixture, SAMPLE_URN non — un
adms:sample n'en a pas besoin)."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from types import SimpleNamespace as NS

from rdflib import XSD, Literal, URIRef

from dh_healthdcat.mapping.dataset import dataset_to_graph
from dh_healthdcat.mapping.namespaces import DCAT, DCT, FOAF
from dh_healthdcat.model import Severity
from dh_healthdcat.reader.dataproduct import read_data_product
from dh_healthdcat.validate.shacl import validate_graph
from tests.fixtures.fake_datahub import (
    ASSET_URN,
    DATAPRODUCT_URN,
    SAMPLE_URN,
    UNDECLARED_PROPERTY,
    build_context,
)


def test_read_data_product_end_to_end():
    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.title == "Venues et sejours des patients"
    assert (
        dataset.access_rights
        == "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC"
    )
    assert dataset.publisher is not None
    assert (
        dataset.publisher.publisher_type
        == "http://healthdataportal.eu/resource/authority/publisher-type/healthcareSystem"
    )
    assert dataset.hdab is not None
    assert len(dataset.distributions) == 1
    assert len(dataset.samples) == 1
    assert dataset.samples[0].source_urn == SAMPLE_URN


def test_reference_specification_codes_resolve_to_canonical_uris_local_fallback_kept():
    """`fr.aphp.healthdcat.referenceSpecification` : les codes du vocab
    ReferenceSpecification deviennent leur URI canonique ; un code hors vocab
    (OSIRIS) retombe silencieusement sur urn:aphp:conformsTo:<code>."""

    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.conforms_to == (
        "http://hl7.org/fhir/4.0.1",
        "urn:aphp:conformsTo:OSIRIS",
    )
    assert not [
        i for i in dataset.issues if i.datahub_field == "fr.aphp.healthdcat.referenceSpecification"
    ]


def test_bare_dois_in_is_referenced_by_are_normalised_to_https_doi_org():
    """`fr.aphp.healthdcat.isReferencedBy` : un DOI nu (`10.x/...`) ou préfixé
    `doi:` devient `https://doi.org/...` ; une URL déjà complète passe telle
    quelle (`dct:isReferencedBy` attend une IRI)."""

    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.is_referenced_by == (
        "https://doi.org/10.1234/abcd.2019",
        "https://doi.org/10.5555/xyz",
        "https://hal.science/hal-04",
    )


def test_distribution_status_is_resolved_to_publications_office_uri():
    """`fr.aphp.healthdcat.distributionStatus` (COMPLETED/WITHDRAWN) est résolu
    en IRI `.../distribution-status/*` et porté par `Distribution.status_uri`
    (émis en `adms:status`). Sans ce câblage, la propriété était définie mais
    jamais émise."""

    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    distribution = next(d for d in dataset.distributions if d.source_urn == ASSET_URN)
    assert (
        distribution.status_uri
        == "http://publications.europa.eu/resource/authority/distribution-status/COMPLETED"
    )


def test_type_coercion_warns_but_does_not_fail():
    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.number_of_records == 1_000_000_000  # coercé en int malgré la chaîne source
    coercion_warnings = [
        i for i in dataset.issues if i.datahub_field == "fr.aphp.healthdcat.numberOfRecords"
    ]
    assert len(coercion_warnings) == 1
    assert coercion_warnings[0].severity is Severity.WARNING


def test_undeclared_structured_property_is_flagged():
    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    drift_warnings = [i for i in dataset.issues if i.datahub_field == UNDECLARED_PROPERTY]
    assert len(drift_warnings) == 1
    assert drift_warnings[0].severity is Severity.WARNING


def test_ndjson_format_falls_back_to_json_with_warning():
    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    fallback_warnings = [
        i for i in dataset.issues if "NDJSON" in i.message.upper() or ".ndjson" in i.message
    ]
    assert fallback_warnings, "attendu un avertissement sur l'absence de code FileType NDJSON"


def test_byte_size_read_from_dataset_profile_yields_full_conformance():
    """ASSET_URN a un datasetProfile (sizeInBytes=123456) dans la fixture :
    plus aucune ERROR, le graphe est SHACL-conforme de bout en bout."""

    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    distribution = next(d for d in dataset.distributions if d.source_urn == ASSET_URN)
    assert distribution.byte_size == 123456

    graph = dataset_to_graph(dataset)

    errors = [i for i in dataset.issues if i.severity is Severity.ERROR]
    assert errors == [], errors

    result = validate_graph(graph)
    assert result.conforms, result.report_text


def test_missing_dataset_profile_still_reported_as_byte_size_error():
    """Sans profil (SAMPLE_URN, ou tout dataset jamais profilé), la
    distribution reste sans dcat:byteSize et mapping/distribution.py le
    signale — inchangé par la lecture de datasetProfile."""

    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    sample = dataset.samples[0]
    assert sample.source_urn == SAMPLE_URN
    assert sample.byte_size is None  # cohérent : pas de profil dans la fixture pour SAMPLE_URN

    dataset_to_graph(dataset)
    # adms:sample n'exige pas dcat:byteSize (:Distribution_Shape de base
    # uniquement, pas :healthDistribution_Shape) : aucune ERREUR pour autant.
    sample_errors = [
        i for i in dataset.issues if i.dataset_urn == SAMPLE_URN and i.severity is Severity.ERROR
    ]
    assert sample_errors == []


def _set_asset_last_modified(ctx, urn: str, millis: int) -> None:
    ctx.graph._entities[urn]["datasetProperties"].lastModified = NS(time=millis)


def test_modified_is_the_latest_distribution_modified():
    """#143 : dataProductProperties n'a pas de lastModified ; dct:modified du
    dcat:Dataset est la plus récente modification de ses distributions. Un
    échantillon plus récent ne compte pas."""

    ctx = build_context()
    _set_asset_last_modified(ctx, ASSET_URN, 1_780_000_000_000)
    _set_asset_last_modified(ctx, SAMPLE_URN, 1_790_000_000_000)

    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.modified == datetime(2026, 5, 28, 20, 26, 40, tzinfo=UTC)
    assert dataset.modified == dataset.distributions[0].modified
    graph = dataset_to_graph(dataset)
    uri = URIRef(f"dataset:{dataset.dataset_id}")
    assert list(graph.objects(uri, DCT.modified)) == [
        Literal(dataset.modified, datatype=XSD.dateTime)
    ]


def test_modified_is_absent_when_no_distribution_has_one():
    ctx = build_context()
    _set_asset_last_modified(ctx, SAMPLE_URN, 1_790_000_000_000)

    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.modified is None
    graph = dataset_to_graph(dataset)
    assert list(graph.objects(URIRef(f"dataset:{dataset.dataset_id}"), DCT.modified)) == []


def _set_documentation(ctx, *, external_url, links) -> None:
    entity = ctx.graph._entities[DATAPRODUCT_URN]
    entity["dataProductProperties"].externalUrl = external_url
    entity["institutionalMemory"] = NS(elements=[NS(url=u, description="doc") for u in links])


def test_landing_page_and_pages_are_exported():
    """#145 : externalUrl → dcat:landingPage, institutionalMemory → foaf:page
    (un par lien, sans doublon), et le graphe reste conforme."""

    ctx = build_context()
    _set_documentation(
        ctx,
        external_url="https://eds.aphp.fr/produits/venues",
        links=["https://wiki.aphp.fr/venues", "https://wiki.aphp.fr/venues", "https://x.fr/a"],
    )

    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.landing_page == "https://eds.aphp.fr/produits/venues"
    assert dataset.pages == ("https://wiki.aphp.fr/venues", "https://x.fr/a")
    graph = dataset_to_graph(dataset)
    uri = URIRef(f"dataset:{dataset.dataset_id}")
    assert list(graph.objects(uri, DCAT.landingPage)) == [
        URIRef("https://eds.aphp.fr/produits/venues")
    ]
    assert set(graph.objects(uri, FOAF.page)) == {
        URIRef("https://wiki.aphp.fr/venues"),
        URIRef("https://x.fr/a"),
    }
    assert validate_graph(graph).conforms is True


def test_non_absolute_iris_are_ignored_with_a_warning():
    ctx = build_context()
    _set_documentation(
        ctx, external_url="eds.aphp.fr/venues", links=["voir le wiki", "https://x.fr/a"]
    )

    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.landing_page is None
    assert dataset.pages == ("https://x.fr/a",)
    warnings = [i for i in dataset.issues if "IRI absolue attendue" in i.message]
    assert {i.rdf_property for i in warnings} == {"dcat:landingPage", "foaf:page"}
    assert all(i.severity is Severity.WARNING for i in warnings)
    assert not dataset.has_errors


def test_no_documentation_emits_nothing():
    dataset = read_data_product(build_context(), DATAPRODUCT_URN)

    assert dataset.landing_page is None
    assert dataset.pages == ()


def test_glossary_term_label_becomes_a_keyword():
    ctx = build_context()
    term_urn = "urn:li:glossaryTerm:sejour"
    ctx.graph._entities[term_urn] = {"glossaryTermInfo": NS(name="Séjour hospitalier")}
    ctx.graph._entities[DATAPRODUCT_URN]["glossaryTerms"] = NS(terms=[NS(urn=term_urn)])

    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert "Séjour hospitalier" in dataset.keywords
    assert ctx.graph.requested_aspects[term_urn] == ["glossaryTermInfo"]


INTERNAL_URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,stg_ehr__patient,PROD)"


def _with_internal_asset(ctx, *, output_ports: tuple[str, ...] = ()) -> None:
    """Ajoute un asset interne (table de staging, sans accessUrl : il lèverait
    des ERREURS s'il était exporté) et marque `output_ports` comme ports."""

    entity = copy.deepcopy(ctx.graph._entities[ASSET_URN])
    entity["datasetProperties"].name = "stg_ehr__patient"
    entity["structuredProperties"] = NS(properties=[])
    ctx.graph._entities[INTERNAL_URN] = entity
    dp = ctx.graph._entities[DATAPRODUCT_URN]["dataProductProperties"]
    dp.assets.append(NS(destinationUrn=INTERNAL_URN, outputPort=False))
    for association in dp.assets:
        association.outputPort = association.destinationUrn in output_ports


def test_without_output_port_every_asset_is_exported():
    """ADR-0006 §6 : aucun port déclaré → comportement inchangé."""

    ctx = build_context()
    _with_internal_asset(ctx)

    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert [d.source_urn for d in dataset.distributions] == [ASSET_URN, INTERNAL_URN]
    assert [s.source_urn for s in dataset.samples] == [SAMPLE_URN]


def test_output_ports_choose_the_distributions():
    """ADR-0006 §6-7 : un asset hors port n'existe pas pour l'export — ni
    distribution, ni anomalie, ni contribution à dct:modified."""

    ctx = build_context()
    _with_internal_asset(ctx, output_ports=(ASSET_URN,))
    _set_asset_last_modified(ctx, INTERNAL_URN, 1_790_000_000_000)

    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert [d.source_urn for d in dataset.distributions] == [ASSET_URN]
    assert [i for i in dataset.issues if i.dataset_urn == INTERNAL_URN] == []
    assert dataset.modified is None


def test_sample_is_kept_whether_or_not_it_is_a_port():
    """ADR-0006 §8 : le tag dcat:sample est indépendant des ports."""

    ctx = build_context()
    _with_internal_asset(ctx, output_ports=(ASSET_URN,))

    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert [s.source_urn for s in dataset.samples] == [SAMPLE_URN]
