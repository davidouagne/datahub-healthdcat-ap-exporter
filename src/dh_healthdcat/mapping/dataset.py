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
    (le CLI export-file s'arrête avant écriture, cf. P0-5/P0-6)."""

    graph = graph if graph is not None else Graph()
    bind_prefixes(graph)

    uri = URIRef(f"dataset:{dataset.dataset_id}")
    graph.add((uri, RDF.type, DCAT.Dataset))
    graph.add((uri, RDF.type, DCAT.Resource))

    # --- Champs obligatoires : dct:identifier, dct:title, dct:description ---
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

    # --- dcat:keyword (>=1) ---
    for kw in dataset.keywords:
        graph.add((uri, DCAT.keyword, Literal(kw)))
    if not dataset.keywords:
        _missing(dataset, "dcat:keyword", "globalTags / glossaryTerms (DataProduct)")

    # --- dcat:theme (>=1, IRI) ---
    for theme in dataset.theme:
        graph.add((uri, DCAT.theme, URIRef(theme)))
    if not dataset.theme:
        _missing(dataset, "dcat:theme", "fr.aphp.healthdcat.theme")

    # --- dct:type (=1) ---
    if dataset.dataset_type:
        graph.add((uri, DCT.type, URIRef(dataset.dataset_type)))
    else:
        _missing(dataset, "dct:type", "fr.aphp.healthdcat.datasetType")

    # --- dct:accessRights (=1) ---
    if dataset.access_rights:
        graph.add((uri, DCT.accessRights, URIRef(dataset.access_rights)))
    else:
        _missing(dataset, "dct:accessRights", "fr.aphp.healthdcat.accessRights")

    # --- dcatap:applicableLegislation (>=1, IRI) ---
    for legislation in dataset.applicable_legislation:
        graph.add((uri, DCATAP.applicableLegislation, URIRef(legislation)))
    if not dataset.applicable_legislation:
        _missing(dataset, "dcatap:applicableLegislation", "fr.aphp.healthdcat.applicableLegislation")

    for lang in dataset.language:
        graph.add((uri, DCT.language, URIRef(lang)))

    # --- Agents ---
    if dataset.publisher:
        agent_mapping.add_publisher(graph, uri, dataset.publisher, dataset.source_urn, dataset.title, dataset.issues)
    else:
        _missing(dataset, "dct:publisher", "owner de type ownershipType:healthdcat.publisher (CorpGroup)")

    if dataset.creator:
        agent_mapping.add_creator(graph, uri, dataset.creator, dataset.source_urn, dataset.title, dataset.issues)

    if dataset.hdab:
        agent_mapping.add_hdab(graph, uri, dataset.hdab, dataset.source_urn, dataset.title, dataset.issues)
    else:
        _missing(dataset, "healthdcatap:hdab", "owner de type ownershipType:healthdcat.hdab (CorpGroup)")

    if dataset.contact_point:
        agent_mapping.add_contact_point(graph, uri, dataset.contact_point, dataset.source_urn, dataset.title, dataset.issues)
    else:
        _missing(dataset, "dcat:contactPoint", "fr.aphp.healthdcat.contactPointName/.contactPointEmail")

    # --- dct:provenance (>=1) ---
    if dataset.provenance:
        prov_node = node_uri("provenance", dataset.source_urn)
        graph.add((uri, DCT.provenance, prov_node))
        graph.add((prov_node, RDF.type, DCT.ProvenanceStatement))
        graph.add((prov_node, RDFS.label, Literal(dataset.provenance, lang="fr")))
    else:
        _missing(dataset, "dct:provenance", "fr.aphp.healthdcat.provenance")

    # --- dpv:hasPurpose (>=1) ---
    if dataset.purpose:
        purpose_node = node_uri("purpose", dataset.source_urn)
        graph.add((uri, DPV.hasPurpose, purpose_node))
        graph.add((purpose_node, RDF.type, DPV.Purpose))
        graph.add((purpose_node, DCT.description, Literal(dataset.purpose, lang="fr")))
    else:
        _missing(dataset, "dpv:hasPurpose", "fr.aphp.healthdcat.purpose")

    # --- healthdcatap:healthCategory / healthTheme (>=1 chacun) ---
    for category in dataset.health_category:
        graph.add((uri, HEALTHDCATAP.healthCategory, URIRef(category)))
    if not dataset.health_category:
        _missing(dataset, "healthdcatap:healthCategory", "fr.aphp.healthdcat.healthCategory")

    for theme in dataset.health_theme:
        graph.add((uri, HEALTHDCATAP.healthTheme, URIRef(theme)))
    if not dataset.health_theme:
        _missing(dataset, "healthdcatap:healthTheme", "fr.aphp.healthdcat.healthTheme")

    # --- dct:spatial (>=1) ---
    for spatial in dataset.spatial:
        graph.add((uri, DCT.spatial, URIRef(spatial)))
    if not dataset.spatial:
        _missing(dataset, "dct:spatial", "fr.aphp.healthdcat.spatialCoverage")

    # --- Champs recommandés / optionnels, sans exigence de cardinalité minimale ---
    if dataset.issued:
        graph.add((uri, DCT.issued, Literal(dataset.issued, datatype=XSD.dateTime)))
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
        agent_mapping.add_period_of_time(graph, uri, DCT.temporal, dataset.temporal, dataset.source_urn + "|temporal")
    if dataset.retention_period:
        agent_mapping.add_period_of_time(
            graph, uri, HEALTHDCATAP.retentionPeriod, dataset.retention_period, dataset.source_urn + "|retention"
        )

    if dataset.number_of_records is not None:
        graph.add((uri, HEALTHDCATAP.numberOfRecords, Literal(dataset.number_of_records, datatype=XSD.nonNegativeInteger)))
    if dataset.number_of_unique_individuals is not None:
        graph.add(
            (uri, HEALTHDCATAP.numberOfUniqueIndividuals, Literal(dataset.number_of_unique_individuals, datatype=XSD.nonNegativeInteger))
        )
    if dataset.min_typical_age is not None:
        graph.add((uri, HEALTHDCATAP.minTypicalAge, Literal(dataset.min_typical_age, datatype=XSD.nonNegativeInteger)))
    if dataset.max_typical_age is not None:
        graph.add((uri, HEALTHDCATAP.maxTypicalAge, Literal(dataset.max_typical_age, datatype=XSD.nonNegativeInteger)))
    if dataset.population_coverage:
        graph.add((uri, HEALTHDCATAP.populationCoverage, Literal(dataset.population_coverage, lang="fr")))

    for coding in dataset.coding_system:
        graph.add((uri, HEALTHDCATAP.hasCodingSystem, URIRef(coding)))

    for basis in dataset.legal_basis:
        graph.add((uri, DPV.hasLegalBasis, URIRef(basis)))

    for pd in dataset.personal_data:
        graph.add((uri, DPV.hasPersonalData, URIRef(pd)))

    # --- Distributions / échantillons ---
    for distribution in dataset.distributions:
        distribution_mapping.add_distribution(graph, uri, distribution, dataset.title, dataset.issues)
    if not dataset.distributions:
        _missing(dataset, "dcat:distribution", "dataProductProperties.assets (aucun asset non marqué dcat:sample)")

    for sample in dataset.samples:
        distribution_mapping.add_distribution(graph, uri, sample, dataset.title, dataset.issues)
    if not dataset.samples:
        _missing(dataset, "adms:sample", "dataProductProperties.assets marqué du tag dcat:sample (aucun trouvé)")

    return graph
