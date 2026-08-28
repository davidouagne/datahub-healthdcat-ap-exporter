"""reader/dataproduct.py contre le double DataHub de tests/fixtures/fake_datahub.py.
Vérifie la coercition tolérante (P0-3), la détection de dérive du référentiel
(P0-2) et la lecture de dcat:byteSize depuis l'aspect timeseries
datasetProfile (ASSET_URN a un profil dans la fixture, SAMPLE_URN non — un
adms:sample n'en a pas besoin)."""

from __future__ import annotations

from dh_healthdcat.mapping.dataset import dataset_to_graph
from dh_healthdcat.model import Severity
from dh_healthdcat.reader.dataproduct import read_data_product
from dh_healthdcat.validate.shacl import validate_graph
from tests.fixtures.fake_datahub import ASSET_URN, DATAPRODUCT_URN, SAMPLE_URN, UNDECLARED_PROPERTY, build_context


def test_read_data_product_end_to_end():
    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.title == "Venues et sejours des patients"
    assert dataset.access_rights == "http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC"
    assert dataset.publisher is not None
    assert dataset.publisher.publisher_type == "http://healthdataportal.eu/resource/authority/publisher-type/healthcareSystem"
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
    assert not [i for i in dataset.issues if i.datahub_field == "fr.aphp.healthdcat.referenceSpecification"]


def test_type_coercion_warns_but_does_not_fail():
    ctx = build_context()
    dataset = read_data_product(ctx, DATAPRODUCT_URN)

    assert dataset.number_of_records == 1_000_000_000  # coercé en int malgré la chaîne source
    coercion_warnings = [i for i in dataset.issues if i.datahub_field == "fr.aphp.healthdcat.numberOfRecords"]
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

    fallback_warnings = [i for i in dataset.issues if "NDJSON" in i.message.upper() or ".ndjson" in i.message]
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
    sample_errors = [i for i in dataset.issues if i.dataset_urn == SAMPLE_URN and i.severity is Severity.ERROR]
    assert sample_errors == []
