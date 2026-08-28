"""HealthDataset (modèle pivot) → dcat:Dataset (graphe rdflib complet).

Orchestre agent.py et distribution.py selon `:Dataset_Shape`
(shapes/ehds/hdap-validator-sensitivity-shape.ttl). Chaque propriété
obligatoire absente est journalisée dans `dataset.issues` plutôt que de faire
échouer la traduction immédiatement — c'est `validate/shacl.py` qui décide,
en aval, si le graphe est exportable (G4/P0-6 : on veut la liste complète des
problèmes en un seul passage, pas un échec au premier champ manquant).

Écart documenté par rapport au fichier de shapes tel que lu : celui-ci utilise
`dqv:hasLegalBasis` (probablement une coquille — `dqv` est le préfixe Data
Quality Vocabulary, sans rapport avec une base légale). Le sérialiseur du HDH
lui-même (`app/form/serializers/dataset.py::to_turtle`) et l'exemple de
référence ckanext-dcat émettent `dpv:hasLegalBasis`, cohérent avec le Data
Privacy Vocabulary. On suit ces deux sources concordantes plutôt que la
coquille supposée du fichier de shapes.
"""

from __future__ import annotations

from rdflib import RDF, XSD, Graph, Literal, URIRef
from rdflib.namespace import RDFS

from dh_healthdcat.mapping import agent as agent_mapping
from dh_healthdcat.mapping import distribution as distribution_mapping
from dh_healthdcat.mapping.namespaces import (
    CSVW,
    DCAT,
    DCATAP,
    DCT,
    DPV,
    FOAF,
    HEALTHDCATAP,
    bind_prefixes,
)
from dh_healthdcat.mapping.nodes import node_uri
from dh_healthdcat.model import HealthDataset, Severity, ValidationIssue


def _missing(dataset: HealthDataset, rdf_property: str, datahub_field: str) -> None:
    dataset.issues.append(
        ValidationIssue(
            severity=Severity.ERROR,
            dataset_name=dataset.title or dataset.source_urn,
            dataset_urn=dataset.source_urn,
            rdf_property=rdf_property,
            datahub_field=datahub_field,
            message="manquant",
        )
    )


def dataset_to_graph(dataset: HealthDataset, graph: Graph | None = None) -> Graph:
    """Traduit un HealthDataset en graphe rdflib. `dataset.issues` est enrichi
    en place ; l'appelant décide quoi faire d'un graphe avec des erreurs
    (le CLI export-file s'arrête avant écriture, cf. P0-5/P0-6).

    Le corps est découpé en `_add_*` par bloc de propriétés : chacun ajoute ses
    triples et journalise ses champs obligatoires absents via `_missing`."""

    graph = graph if graph is not None else Graph()
    bind_prefixes(graph)

    uri = URIRef(f"dataset:{dataset.dataset_id}")
    graph.add((uri, RDF.type, DCAT.Dataset))
    graph.add((uri, RDF.type, DCAT.Resource))

    _add_mandatory_core(graph, uri, dataset)
    _add_classification(graph, uri, dataset)
    _add_agents(graph, uri, dataset)
    _add_provenance_and_purpose(graph, uri, dataset)
    _add_health_coverage(graph, uri, dataset)
    _add_optional_metadata(graph, uri, dataset)
    _add_quantitative_metadata(graph, uri, dataset)
    _add_semantic_and_legal(graph, uri, dataset)
    _add_distributions(graph, uri, dataset)

    return graph


def _add_mandatory_core(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """dct:identifier / title / description (+ dct:alternative optionnel)."""

    graph.add((uri, DCT.identifier, Literal(dataset.identifier, datatype=XSD.anyURI)))
    if dataset.title:
        graph.add((uri, DCT.title, Literal(dataset.title, lang="fr")))
    else:
        _missing(dataset, "dct:title", "dataProductProperties.name")
    if dataset.description:
        graph.add((uri, DCT.description, Literal(dataset.description, lang="fr")))
    else:
        _missing(dataset, "dct:description", "dataProductProperties.description")

    if dataset.acronym:
        graph.add((uri, DCT.alternative, Literal(dataset.acronym)))


def _add_classification(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """dcat:keyword / theme, dct:type / accessRights / language,
    dcatap:applicableLegislation."""

    for kw in dataset.keywords:
        graph.add((uri, DCAT.keyword, Literal(kw)))
    if not dataset.keywords:
        _missing(dataset, "dcat:keyword", "globalTags / glossaryTerms (DataProduct)")

    for theme in dataset.theme:
        graph.add((uri, DCAT.theme, URIRef(theme)))
    if not dataset.theme:
        _missing(dataset, "dcat:theme", "fr.aphp.healthdcat.theme")

    if dataset.dataset_type:
        graph.add((uri, DCT.type, URIRef(dataset.dataset_type)))
    else:
        _missing(dataset, "dct:type", "fr.aphp.healthdcat.datasetType")

    if dataset.access_rights:
        graph.add((uri, DCT.accessRights, URIRef(dataset.access_rights)))
    else:
        _missing(dataset, "dct:accessRights", "fr.aphp.healthdcat.accessRights")

    for legislation in dataset.applicable_legislation:
        graph.add((uri, DCATAP.applicableLegislation, URIRef(legislation)))
    if not dataset.applicable_legislation:
        _missing(
            dataset, "dcatap:applicableLegislation", "fr.aphp.healthdcat.applicableLegislation"
        )

    for lang in dataset.language:
        graph.add((uri, DCT.language, URIRef(lang)))


def _add_agents(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """dct:publisher / creator, healthdcatap:hdab, dcat:contactPoint."""

    if dataset.publisher:
        agent_mapping.add_publisher(
            graph, uri, dataset.publisher, dataset.source_urn, dataset.title, dataset.issues
        )
    else:
        _missing(
            dataset, "dct:publisher", "owner de type ownershipType:healthdcat.publisher (CorpGroup)"
        )

    if dataset.creator:
        agent_mapping.add_creator(
            graph, uri, dataset.creator, dataset.source_urn, dataset.title, dataset.issues
        )

    if dataset.hdab:
        agent_mapping.add_hdab(
            graph, uri, dataset.hdab, dataset.source_urn, dataset.title, dataset.issues
        )
    else:
        _missing(
            dataset, "healthdcatap:hdab", "owner de type ownershipType:healthdcat.hdab (CorpGroup)"
        )

    if dataset.contact_point:
        agent_mapping.add_contact_point(
            graph, uri, dataset.contact_point, dataset.source_urn, dataset.title, dataset.issues
        )
    else:
        _missing(
            dataset, "dcat:contactPoint", "fr.aphp.healthdcat.contactPointName/.contactPointEmail"
        )


def _add_provenance_and_purpose(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """dct:provenance → dct:ProvenanceStatement, dpv:hasPurpose → dpv:Purpose."""

    if dataset.provenance:
        prov_node = node_uri("provenance", dataset.source_urn)
        graph.add((uri, DCT.provenance, prov_node))
        graph.add((prov_node, RDF.type, DCT.ProvenanceStatement))
        graph.add((prov_node, RDFS.label, Literal(dataset.provenance, lang="fr")))
    else:
        _missing(dataset, "dct:provenance", "fr.aphp.healthdcat.provenance")

    if dataset.purpose:
        purpose_node = node_uri("purpose", dataset.source_urn)
        graph.add((uri, DPV.hasPurpose, purpose_node))
        graph.add((purpose_node, RDF.type, DPV.Purpose))
        graph.add((purpose_node, DCT.description, Literal(dataset.purpose, lang="fr")))
    else:
        _missing(dataset, "dpv:hasPurpose", "fr.aphp.healthdcat.purpose")


def _add_health_coverage(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """healthdcatap:healthCategory / healthTheme, dct:spatial (>=1 chacun)."""

    for category in dataset.health_category:
        graph.add((uri, HEALTHDCATAP.healthCategory, URIRef(category)))
    if not dataset.health_category:
        _missing(dataset, "healthdcatap:healthCategory", "fr.aphp.healthdcat.healthCategory")

    for theme in dataset.health_theme:
        graph.add((uri, HEALTHDCATAP.healthTheme, URIRef(theme)))
    if not dataset.health_theme:
        _missing(dataset, "healthdcatap:healthTheme", "fr.aphp.healthdcat.healthTheme")

    for spatial in dataset.spatial:
        graph.add((uri, DCT.spatial, URIRef(spatial)))
    if not dataset.spatial:
        _missing(dataset, "dct:spatial", "fr.aphp.healthdcat.spatialCoverage")


def _add_optional_metadata(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """Champs recommandés / optionnels, sans cardinalité minimale."""

    if dataset.issued:
        graph.add((uri, DCT.issued, Literal(dataset.issued, datatype=XSD.date)))
    if dataset.modified:
        graph.add((uri, DCT.modified, Literal(dataset.modified, datatype=XSD.dateTime)))
    if dataset.accrual_periodicity:
        graph.add((uri, DCT.accrualPeriodicity, URIRef(dataset.accrual_periodicity)))
    if dataset.license:
        graph.add((uri, DCT.license, URIRef(dataset.license)))
    for ref in dataset.is_referenced_by:
        graph.add((uri, DCT.isReferencedBy, URIRef(ref)))
    for conforms in dataset.conforms_to:
        graph.add((uri, DCT.conformsTo, URIRef(conforms)))
    for page in dataset.pages:
        graph.add((uri, FOAF.page, URIRef(page)))

    if dataset.temporal:
        agent_mapping.add_period_of_time(
            graph, uri, DCT.temporal, dataset.temporal, dataset.source_urn + "|temporal"
        )
    if dataset.retention_period:
        agent_mapping.add_period_of_time(
            graph,
            uri,
            HEALTHDCATAP.retentionPeriod,
            dataset.retention_period,
            dataset.source_urn + "|retention",
        )


def _add_quantitative_metadata(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """Dénombrements et tranches d'âge (healthdcatap, xsd:nonNegativeInteger)."""

    counts = (
        (HEALTHDCATAP.numberOfRecords, dataset.number_of_records),
        (HEALTHDCATAP.numberOfUniqueIndividuals, dataset.number_of_unique_individuals),
        (HEALTHDCATAP.minTypicalAge, dataset.min_typical_age),
        (HEALTHDCATAP.maxTypicalAge, dataset.max_typical_age),
    )
    for predicate, value in counts:
        if value is not None:
            graph.add((uri, predicate, Literal(value, datatype=XSD.nonNegativeInteger)))

    if dataset.population_coverage:
        graph.add(
            (uri, HEALTHDCATAP.populationCoverage, Literal(dataset.population_coverage, lang="fr"))
        )


def _add_semantic_and_legal(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """healthdcatap:hasCodingSystem, dpv:hasLegalBasis / hasPersonalData,
    healthdcatap:hasStructuredData (toujours émis, `false` compris — R7)."""

    for coding in dataset.coding_system:
        graph.add((uri, HEALTHDCATAP.hasCodingSystem, URIRef(coding)))
    for basis in dataset.legal_basis:
        graph.add((uri, DPV.hasLegalBasis, URIRef(basis)))
    for pd in dataset.personal_data:
        graph.add((uri, DPV.hasPersonalData, URIRef(pd)))

    graph.add(
        (
            uri,
            HEALTHDCATAP.hasStructuredData,
            Literal(dataset.has_structured_data, datatype=XSD.boolean),
        )
    )


def _add_distributions(graph: Graph, uri: URIRef, dataset: HealthDataset) -> None:
    """dcat:distribution / adms:sample, puis healthdcatap:hasVariables →
    csvw:TableGroup regroupant toutes les csvw:Table du dataset (R7)."""

    table_nodes: list[URIRef] = []
    for distribution in dataset.distributions:
        _, table_node = distribution_mapping.add_distribution(
            graph, uri, distribution, dataset.title, dataset.issues
        )
        if table_node is not None:
            table_nodes.append(table_node)
    if not dataset.distributions:
        _missing(
            dataset,
            "dcat:distribution",
            "dataProductProperties.assets (aucun asset non marqué dcat:sample)",
        )

    for sample in dataset.samples:
        _, table_node = distribution_mapping.add_distribution(
            graph, uri, sample, dataset.title, dataset.issues
        )
        if table_node is not None:
            table_nodes.append(table_node)
    if not dataset.samples:
        _missing(
            dataset,
            "adms:sample",
            "dataProductProperties.assets marqué du tag dcat:sample (aucun trouvé)",
        )

    # Le validateur HDH n'a pas de shape TableGroup et :Dataset_Shape n'est pas
    # sh:closed — l'émission est sans effet sur lui (hasVariables interdit si
    # hasStructuredData est faux, ce qui coïncide avec « aucune table »).
    if table_nodes:
        table_group = node_uri("tablegroup", str(uri))
        graph.add((uri, HEALTHDCATAP.hasVariables, table_group))
        graph.add((table_group, RDF.type, CSVW.TableGroup))
        for table_node in table_nodes:
            graph.add((table_group, CSVW.table, table_node))
