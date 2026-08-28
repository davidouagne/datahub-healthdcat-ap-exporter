"""dcat:Distribution / adms:sample / csvw:Table → triples RDF.

Contraintes SHACL (shapes/ehds/hdap-validator-sensitivity-shape.ttl) :

- `:Distribution_Shape` (base, s'applique aussi aux adms:sample) :
  dcat:accessURL ≥1 (BlankNodeOrIRI).
- `:healthDistribution_Shape` (dcat:distribution UNIQUEMENT, pas les samples) :
  étend Distribution_Shape avec dcatap:applicableLegislation ≥1 IRI,
  dcat:byteSize =1 xsd:nonNegativeInteger, dct:format =1, dct:rights =1.
  → un adms:sample n'a donc besoin que d'une dcat:accessURL pour être valide ;
    un dcat:distribution a des exigences bien plus strictes.
- `:CSVWTableShape` : dct:title ≥1, csvw:column ≥1.
- `:CSVWColumnShape` : csvw:name ≥1, csvw:titles ≥1, csvw:datatype ≥1.
"""

from __future__ import annotations

from rdflib import RDF, XSD, Graph, Literal, URIRef
from rdflib.namespace import RDFS

from dh_healthdcat.mapping.namespaces import ADMS, CSVW, DCAT, DCATAP, DCT
from dh_healthdcat.mapping.nodes import node_uri
from dh_healthdcat.model import Distribution, Severity, Table, ValidationIssue


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


def add_distribution(
    graph: Graph,
    dataset_uri: URIRef,
    distribution: Distribution,
    dataset_name: str,
    issues: list[ValidationIssue],
) -> tuple[URIRef, URIRef | None]:
    """Ajoute un dcat:distribution ou adms:sample selon `distribution.is_sample`.

    Renvoie `(nœud distribution, nœud csvw:Table | None)` — l'appelant
    (`mapping/dataset.py`) collecte les nœuds table pour les regrouper sous le
    `csvw:TableGroup` porté par `healthdcatap:hasVariables`."""

    kind = "sample" if distribution.is_sample else "distribution"
    node = node_uri(kind, distribution.source_urn or distribution.node_id)
    predicate = ADMS.sample if distribution.is_sample else DCAT.distribution
    graph.add((dataset_uri, predicate, node))
    graph.add((node, RDF.type, DCAT.Distribution))

    _add_distribution_properties(graph, node, distribution, dataset_name, issues)

    if not distribution.is_sample:
        _check_health_distribution_required(distribution, dataset_name, issues)

    table_node = None
    if distribution.table is not None:
        table_node = _add_table(graph, node, distribution, distribution.table)

    return node, table_node


def _add_distribution_properties(
    graph: Graph,
    node: URIRef,
    distribution: Distribution,
    dataset_name: str,
    issues: list[ValidationIssue],
) -> None:
    """Propriétés scalaires du nœud distribution/sample (dcat:accessURL exigé =1
    par :Distribution_Shape, le reste optionnel à ce niveau)."""

    if distribution.title:
        graph.add((node, DCT.title, Literal(distribution.title)))
    if distribution.description:
        graph.add((node, DCT.description, Literal(distribution.description, lang="fr")))

    if distribution.access_url:
        graph.add((node, DCAT.accessURL, URIRef(distribution.access_url)))
    else:
        _missing(
            issues,
            dataset_name,
            dataset_urn_or_source(distribution),
            "dcat:accessURL",
            f"fr.aphp.healthdcat.accessUrl (Dataset {distribution.title})",
        )

    # Prédicats optionnels pointant vers une IRI unique.
    optional_iris = (
        (DCAT.downloadURL, distribution.download_url),
        (DCAT.mediaType, distribution.media_type_uri),
        (ADMS.status, distribution.status_uri),
        (DCT.format, distribution.format_uri),
    )
    for predicate, value in optional_iris:
        if value:
            graph.add((node, predicate, URIRef(value)))

    if distribution.issued:
        graph.add((node, DCT.issued, Literal(distribution.issued, datatype=XSD.dateTime)))
    if distribution.modified:
        graph.add((node, DCT.modified, Literal(distribution.modified, datatype=XSD.dateTime)))

    for legislation in distribution.applicable_legislation:
        graph.add((node, DCATAP.applicableLegislation, URIRef(legislation)))

    if distribution.rights:
        _add_distribution_rights(graph, node, distribution.rights)
    if distribution.byte_size is not None:
        graph.add(
            (node, DCAT.byteSize, Literal(distribution.byte_size, datatype=XSD.nonNegativeInteger))
        )


def _add_distribution_rights(graph: Graph, node: URIRef, rights: str) -> None:
    """dct:rights doit être sh:BlankNodeOrIRI, jamais un littéral direct
    (pyshacl NodeKindConstraintComponent) : on pointe vers un
    dct:RightsStatement plutôt que d'attacher le texte directement."""

    rights_node = node_uri("rights", str(node))
    graph.add((node, DCT.rights, rights_node))
    graph.add((rights_node, RDF.type, DCT.RightsStatement))
    graph.add((rights_node, RDFS.label, Literal(rights, lang="fr")))


def _check_health_distribution_required(
    distribution: Distribution, dataset_name: str, issues: list[ValidationIssue]
) -> None:
    """:healthDistribution_Shape impose applicableLegislation / byteSize /
    format / rights aux `dcat:distribution` seulement, pas aux `adms:sample`."""

    urn = dataset_urn_or_source(distribution)
    if not distribution.applicable_legislation:
        _missing(
            issues,
            dataset_name,
            urn,
            "dcatap:applicableLegislation",
            "hérité du DataProduct — vérifier fr.aphp.healthdcat.applicableLegislation",
        )
    if distribution.byte_size is None:
        _missing(
            issues,
            dataset_name,
            urn,
            "dcat:byteSize",
            f"profil DataHub absent pour {distribution.title} (datasetProfile.sizeInBytes)",
        )
    if not distribution.format_uri:
        _missing(
            issues,
            dataset_name,
            urn,
            "dct:format",
            f"fr.aphp.healthdcat.distributionFormat (Dataset {distribution.title})",
        )
    if not distribution.rights:
        _missing(
            issues,
            dataset_name,
            urn,
            "dct:rights",
            "fr.aphp.healthdcat.license (DataProduct, hérité)",
        )


def dataset_urn_or_source(distribution: Distribution) -> str:
    """Petit raccourci : le message d'erreur doit citer le Dataset DataHub source,
    pas le DataProduct parent, pour que le steward sache où corriger."""

    return distribution.source_urn


def _add_table(
    graph: Graph, distribution_node: URIRef, distribution: Distribution, table: Table
) -> URIRef:
    """csvw:Table. Aucun prédicat Distribution→Table n'est défini par les shapes HDH
    (:CSVWTableShape cible juste `csvw:Table` en isolation) ; on relie table et
    distribution par le même `csvw:url` que `dcat:accessURL` plutôt que
    d'inventer un prédicat. Le rattachement R7 se fait en amont, au niveau
    `dcat:Dataset` : `mapping/dataset.py` regroupe le nœud renvoyé ici sous un
    `csvw:TableGroup` porté par `healthdcatap:hasVariables`."""

    table_node = node_uri("table", str(distribution_node))
    graph.add((table_node, RDF.type, CSVW.Table))
    graph.add((table_node, DCT.title, Literal(table.title)))
    if distribution.access_url:
        graph.add((table_node, CSVW.url, URIRef(distribution.access_url)))

    primary_keys = [c.name for c in table.columns if c.is_primary_key]
    for pk_name in primary_keys:
        graph.add((table_node, CSVW.primaryKey, Literal(pk_name)))

    for column in table.columns:
        column_node = node_uri("column", str(table_node), column.name)
        graph.add((table_node, CSVW.column, column_node))
        graph.add((column_node, RDF.type, CSVW.Column))
        graph.add((column_node, CSVW.name, Literal(column.name)))
        graph.add((column_node, CSVW.titles, Literal(column.name)))
        graph.add((column_node, CSVW.datatype, Literal(column.datatype)))
        if column.description:
            graph.add((column_node, DCT.description, Literal(column.description, lang="fr")))

    return table_node
