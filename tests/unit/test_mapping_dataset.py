"""Le mapping pivot -> RDF produit un graphe conforme SHACL quand tous les
champs obligatoires sont renseignés, et signale précisément ce qui manque
sinon. Aucune dépendance réseau ni DataHub : le modèle pivot est construit
à la main (voir model.py)."""

from __future__ import annotations

from datetime import date, datetime

from rdflib import RDF, XSD, Literal

from dh_healthdcat.mapping import vocabularies as v
from dh_healthdcat.mapping.dataset import dataset_to_graph
from dh_healthdcat.mapping.namespaces import CSVW, HEALTHDCATAP
from dh_healthdcat.model import (
    Agent,
    Column,
    ContactPoint,
    Distribution,
    HealthDataset,
    PeriodOfTime,
    Severity,
    Table,
)
from dh_healthdcat.validate.shacl import validate_graph


def _fully_conformant_dataset() -> HealthDataset:
    hdab = Agent(name="Health Data Hub", homepage="https://health-data-hub.fr", mbox="contact@health-data-hub.fr")
    publisher = Agent(
        name="Assistance Publique - Hopitaux de Paris",
        homepage="https://www.aphp.fr",
        mbox="eds-contact@aphp.fr",
        publisher_type=v.PUBLISHER_TYPE.resolve("Hospital or Healthcare System"),
        publisher_note="EDS de l'AP-HP",
        trusted_data_holder=True,
    )
    cp = ContactPoint(name="Coordination EDS", email="eds-coord@aphp.fr", url="https://eds.aphp.fr")

    table = Table(
        title="Patient",
        columns=(Column(name="id", description="Identifiant logique", datatype="string", is_primary_key=True),),
    )
    dist = Distribution(
        node_id="dist-1",
        title="Patient.ndjson",
        is_sample=False,
        access_url="https://s3.aphp.fr/sharing-layer/Patient.ndjson",
        byte_size=123456,
        format_uri=v.FILE_TYPE.resolve("JSON"),
        rights="Usage restreint EDS",
        applicable_legislation=(v.APPLICABLE_REGULATIONS.resolve("COMMISSION IMPLEMENTING REGULATION (EU) 2023/138"),),
        source_urn="urn:li:dataset:(urn:li:dataPlatform:s3,sharing_layer_Patient.ndjson,PROD)",
    )
    sample = Distribution(
        node_id="sample-1",
        title="Echantillon Patient",
        is_sample=True,
        access_url="https://s3.aphp.fr/sharing-layer/Patient.sample.ndjson",
        source_urn="urn:li:dataset:(urn:li:dataPlatform:s3,sharing_layer_Patient_sample.ndjson,PROD)",
        table=table,
    )

    return HealthDataset(
        source_urn="urn:li:dataProduct:b78435bfad26dab4c11e6e41c2a72b53",
        dataset_id="b78435bfad26dab4c11e6e41c2a72b53",
        identifier="https://eds.aphp.fr/dataset/b78435bfad26dab4c11e6e41c2a72b53",
        title="Venues et sejours des patients",
        description="Enregistrements de venues et sejours des patients a l'AP-HP.",
        keywords=("EDS", "ORBIS"),
        theme=(v.DATA_THEME_HEALTH,),
        dataset_type=v.DATASET_TYPE.resolve("PERSONAL_DATA"),
        access_rights=v.ACCESS_RIGHTS.resolve("NON_PUBLIC"),
        applicable_legislation=(v.APPLICABLE_REGULATIONS.resolve("COMMISSION IMPLEMENTING REGULATION (EU) 2023/138"),),
        language=(v.LANGUAGE.resolve("FRA"),),
        publisher=publisher,
        hdab=hdab,
        contact_point=cp,
        provenance="Donnees issues du dossier patient informatise ORBIS.",
        purpose="Recherche et pilotage de l'activite hospitaliere.",
        health_category=(v.HEALTH_CATEGORY.resolve("HRAD"),),
        health_theme=(v.HEALTH_THEME.resolve("health_systems"),),
        spatial=(v.COUNTRY.resolve("FRA"),),
        issued=datetime(2019, 1, 1),
        modified=datetime(2026, 8, 1),
        accrual_periodicity=v.FREQUENCY.resolve("DAILY"),
        number_of_records=1_000_000_000,
        temporal=PeriodOfTime(start_date=date(2019, 1, 1)),
        distributions=(dist,),
        samples=(sample,),
    )


def test_fully_populated_dataset_conforms_to_shacl():
    dataset = _fully_conformant_dataset()
    graph = dataset_to_graph(dataset)

    assert dataset.issues == []
    result = validate_graph(graph)
    assert result.conforms, result.report_text


def test_missing_required_fields_are_reported_with_datahub_field_name():
    dataset = HealthDataset(
        source_urn="urn:li:dataProduct:empty",
        dataset_id="empty",
        identifier="https://eds.aphp.fr/dataset/empty",
        title="Jeu incomplet",
        description="Un jeu de test volontairement vide.",
    )

    graph = dataset_to_graph(dataset)
    result = validate_graph(graph)

    assert dataset.has_errors
    assert not result.conforms

    by_property = {i.rdf_property: i for i in dataset.issues if i.severity is Severity.ERROR}
    assert "healthdcatap:healthTheme" in by_property
    assert by_property["healthdcatap:healthTheme"].datahub_field == "fr.aphp.healthdcat.healthTheme"
    assert "dcat:distribution" in by_property
    assert "adms:sample" in by_property
    assert "dct:publisher" in by_property
    assert "healthdcatap:hdab" in by_property


def test_has_structured_data_true_when_an_asset_carries_a_schema():
    """healthdcatap:hasStructuredData (xsd:boolean, 1..1 en R7) se dérive :
    `true` dès qu'au moins un asset (distribution ou sample) porte un schéma
    (`csvw:Table` construite depuis `schemaMetadata`)."""

    dataset = _fully_conformant_dataset()  # le sample porte déjà une Table
    graph = dataset_to_graph(dataset)
    dataset_uri = next(graph.subjects(HEALTHDCATAP.hasStructuredData, None))
    values = list(graph.objects(dataset_uri, HEALTHDCATAP.hasStructuredData))

    assert values == [Literal(True, datatype=XSD.boolean)]


def test_has_structured_data_false_is_emitted_when_no_asset_carries_a_schema():
    """La cardinalité R7 est 1..1 : le booléen est toujours émis, `false`
    compris, quand aucun asset ne porte de schéma."""

    dataset = _fully_conformant_dataset()
    dataset.samples = (
        Distribution(
            node_id=dataset.samples[0].node_id,
            title=dataset.samples[0].title,
            is_sample=True,
            access_url=dataset.samples[0].access_url,
            source_urn=dataset.samples[0].source_urn,
        ),
    )
    assert all(d.table is None for d in (*dataset.distributions, *dataset.samples))

    graph = dataset_to_graph(dataset)
    dataset_uri = next(graph.subjects(HEALTHDCATAP.hasStructuredData, None))
    values = list(graph.objects(dataset_uri, HEALTHDCATAP.hasStructuredData))

    assert values == [Literal(False, datatype=XSD.boolean)]


def test_has_variables_groups_every_csvw_table_under_one_tablegroup():
    """healthdcatap:hasVariables → csvw:TableGroup au niveau du dcat:Dataset,
    regroupant par csvw:table toutes les csvw:Table déjà produites depuis
    schemaMetadata (distributions comme échantillons)."""

    dataset = _fully_conformant_dataset()  # 1 csvw:Table, portée par le sample
    graph = dataset_to_graph(dataset)

    dataset_uri = next(graph.subjects(HEALTHDCATAP.hasVariables, None))
    groups = list(graph.objects(dataset_uri, HEALTHDCATAP.hasVariables))
    assert len(groups) == 1
    table_group = groups[0]
    assert (table_group, RDF.type, CSVW.TableGroup) in graph

    grouped = set(graph.objects(table_group, CSVW.table))
    all_tables = set(graph.subjects(RDF.type, CSVW.Table))
    assert grouped == all_tables
    assert len(grouped) == 1


def test_no_tablegroup_when_no_asset_carries_a_schema():
    """R7 interdit healthdcatap:hasVariables quand hasStructuredData est faux :
    aucune table → aucun csvw:TableGroup, aucun hasVariables."""

    dataset = _fully_conformant_dataset()
    dataset.samples = (
        Distribution(
            node_id=dataset.samples[0].node_id,
            title=dataset.samples[0].title,
            is_sample=True,
            access_url=dataset.samples[0].access_url,
            source_urn=dataset.samples[0].source_urn,
        ),
    )

    graph = dataset_to_graph(dataset)

    assert list(graph.objects(None, HEALTHDCATAP.hasVariables)) == []
    assert list(graph.subjects(RDF.type, CSVW.TableGroup)) == []


def test_distribution_requires_stricter_fields_than_sample():
    """:healthDistribution_Shape n'impose byteSize/format/rights/applicableLegislation
    qu'aux dcat:distribution, pas aux adms:sample — un sample avec seule une
    accessURL doit rester valide."""

    dataset = _fully_conformant_dataset()
    # Retire les champs stricts de la distribution mais garde le sample minimal.
    stripped = dataset.distributions[0]
    dataset.distributions = (
        Distribution(
            node_id=stripped.node_id,
            title=stripped.title,
            is_sample=False,
            access_url=stripped.access_url,
            source_urn=stripped.source_urn,
        ),
    )

    graph = dataset_to_graph(dataset)

    by_property = {i.rdf_property for i in dataset.issues if i.severity is Severity.ERROR}
    assert "dcat:byteSize" in by_property
    assert "dct:format" in by_property
    assert "dct:rights" in by_property
    # Le sample, lui, ne doit déclencher aucune de ces erreurs.
    sample_issues = [i for i in dataset.issues if i.dataset_urn == dataset.samples[0].source_urn]
    assert not any(i.rdf_property in ("dcat:byteSize", "dct:format", "dct:rights") for i in sample_issues)
