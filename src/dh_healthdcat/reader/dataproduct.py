"""DataProduct DataHub → HealthDataset (modèle pivot complet).

Orchestre reader/props.py, reader/agents.py et reader/dataset.py. C'est ici
que les codes courts des structured properties sont résolus vers des URI
d'autorité via `mapping/vocabularies.py` — un code hors vocabulaire ne fait
pas échouer tout l'export : il est journalisé en `Severity.WARNING` et
ignoré, cohérent avec la philosophie « rapport complet en un passage » de
G4/P0-6.
"""

from __future__ import annotations

from datetime import datetime

from dh_healthdcat.mapping import vocabularies as v
from dh_healthdcat.mapping.vocabularies import (
    UnknownVocabularyValueError,
    Vocabulary,
    resolve_many_or_warn,
    resolve_or_warn,
)
from dh_healthdcat.model import Agent, HealthDataset, PeriodOfTime, Severity, ValidationIssue
from dh_healthdcat.reader import agents as agents_reader
from dh_healthdcat.reader import dataset as dataset_reader
from dh_healthdcat.reader import props
from dh_healthdcat.reader.graph import ReadContext

DEFAULT_BASE_URI = "https://eds.aphp.fr"


def _dataset_id_from_urn(urn: str) -> str:
    return urn.rsplit(":", 1)[-1]


def _warn_undeclared_properties(
    ctx: ReadContext,
    entity,  # noqa: ANN001 - SemitypedEntity
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> None:
    """Signale toute structured property assignée sur l'entité mais absente du
    référentiel (`ctx.property_definitions`, chargé une fois via
    `StructuredProperties.list()` — P0-2). Un cas typique : une propriété
    renommée ou retirée d'`assets.yml` mais encore assignée sur d'anciens
    DataProducts — un signe de dérive qu'on veut voir, pas laisser filer en
    silence."""

    aspect = entity.get("structuredProperties")
    if aspect is None:
        return
    known = ctx.property_definitions
    for assignment in aspect.properties:
        qualified_name = assignment.propertyUrn.removeprefix(props.STRUCTURED_PROPERTY_PREFIX)
        if qualified_name not in known:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    dataset_name=dataset_name,
                    dataset_urn=dataset_urn,
                    rdf_property="(référentiel)",
                    datahub_field=qualified_name,
                    message="propriété structurée assignée mais absente du référentiel DataHub (assets.yml a-t-il changé ?)",
                )
            )


def _resolve_many(
    vocab: Vocabulary,
    codes: tuple[str, ...],
    dataset_name: str,
    dataset_urn: str,
    datahub_field: str,
    issues: list[ValidationIssue],
) -> tuple[str, ...]:
    return resolve_many_or_warn(
        vocab, codes, dataset_name=dataset_name, dataset_urn=dataset_urn, datahub_field=datahub_field, issues=issues
    )


def _resolve_one(
    vocab: Vocabulary,
    code: str | None,
    dataset_name: str,
    dataset_urn: str,
    datahub_field: str,
    issues: list[ValidationIssue],
) -> str | None:
    return resolve_or_warn(
        vocab, code, dataset_name=dataset_name, dataset_urn=dataset_urn, datahub_field=datahub_field, issues=issues
    )


def _as_uri(value: str | None, urn_namespace: str) -> str | None:
    """Si `value` ressemble déjà à une URI, le renvoie tel quel ; sinon
    l'enveloppe dans un URN stable pour rester `sh:nodeKind sh:IRI`-compatible
    (ex. dct:conformsTo attend une IRI, pas un code libre)."""

    if value is None:
        return None
    if value.startswith("http://") or value.startswith("https://") or ":" in value.split("/")[0]:
        return value
    return f"urn:{urn_namespace}:{value}"


def read_data_product(
    ctx: ReadContext,
    dataproduct_urn: str,
    *,
    base_uri: str = DEFAULT_BASE_URI,
) -> HealthDataset:
    entity = ctx.get_entity(dataproduct_urn)
    dp = entity.get("dataProductProperties")
    if dp is None or not dp.name:
        raise ValueError(f"{dataproduct_urn} n'a pas de dataProductProperties.name — DataProduct invalide ou introuvable")

    dataset_id = _dataset_id_from_urn(dataproduct_urn)
    title = dp.name
    description = dp.description or ""
    issues: list[ValidationIssue] = []
    _warn_undeclared_properties(ctx, entity, title, dataproduct_urn, issues)

    # --- Mots-clés : tags "porteurs de sens" + libellés des glossary terms ---
    keywords: list[str] = []
    tags = entity.get("globalTags")
    if tags:
        for t in tags.tags:
            local = t.tag.rsplit(":", 1)[-1]
            if local not in ("dcat:sample",):
                keywords.append(local)
    glossary = entity.get("glossaryTerms")
    if glossary:
        for term in glossary.terms:
            term_entity = ctx.get_entity(term.urn)
            info = term_entity.get("glossaryTermInfo")
            keywords.append(info.name if info and info.name else term.urn.rsplit(":", 1)[-1])

    # --- Champs structured properties, valeurs simples ---
    acronym = props.get_string(ctx, entity, "fr.aphp.healthdcat.acronym", title, dataproduct_urn, issues)
    dataset_type = _resolve_one(
        v.DATASET_TYPE,
        props.get_string(ctx, entity, "fr.aphp.healthdcat.datasetType", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.datasetType", issues,
    )
    access_rights = _resolve_one(
        v.ACCESS_RIGHTS,
        props.get_string(ctx, entity, "fr.aphp.healthdcat.accessRights", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.accessRights", issues,
    )
    applicable_legislation = _resolve_many(
        v.APPLICABLE_REGULATIONS,
        props.get_strings(ctx, entity, "fr.aphp.healthdcat.applicableLegislation", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.applicableLegislation", issues,
    )
    health_category = _resolve_many(
        v.HEALTH_CATEGORY,
        props.get_strings(ctx, entity, "fr.aphp.healthdcat.healthCategory", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.healthCategory", issues,
    )
    health_theme = _resolve_many(
        v.HEALTH_THEME,
        props.get_strings(ctx, entity, "fr.aphp.healthdcat.healthTheme", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.healthTheme", issues,
    )
    personal_data = _resolve_many(
        v.PERSONAL_DATA,
        props.get_strings(ctx, entity, "fr.aphp.healthdcat.personalData", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.personalData", issues,
    )
    language = _resolve_many(
        v.LANGUAGE,
        props.get_strings(ctx, entity, "fr.aphp.healthdcat.language", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.language", issues,
    )
    legal_basis = _resolve_many(
        v.LEGAL_BASIS,
        props.get_strings(ctx, entity, "fr.aphp.healthdcat.legalBasis", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.legalBasis", issues,
    )
    coding_system = _resolve_many(
        v.CODING_SYSTEM,
        props.get_strings(ctx, entity, "fr.aphp.healthdcat.coding", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.coding", issues,
    )
    accrual_periodicity = _resolve_one(
        v.FREQUENCY,
        props.get_string(ctx, entity, "fr.aphp.healthdcat.publishingFrequency", title, dataproduct_urn, issues),
        title, dataproduct_urn, "fr.aphp.healthdcat.publishingFrequency", issues,
    )

    spatial_raw = props.get_strings(ctx, entity, "fr.aphp.healthdcat.spatialCoverage", title, dataproduct_urn, issues)
    spatial: list[str] = []
    for code in spatial_raw:
        if code.startswith("http"):
            spatial.append(code)
            continue
        try:
            spatial.append(v.COUNTRY.resolve(code))
        except UnknownVocabularyValueError:
            spatial.append(code)  # déjà une URI d'un autre référentiel (GeoNames...) ou code régional (FR-75)

    conforms_to: list[str] = []
    for code in props.get_strings(ctx, entity, "fr.aphp.healthdcat.referenceSpecification", title, dataproduct_urn, issues):
        try:
            conforms_to.append(v.REFERENCE_SPECIFICATION.resolve(code))
        except UnknownVocabularyValueError:
            fallback = _as_uri(code, "aphp:conformsTo")  # OSIRIS & co. → urn:aphp:conformsTo:<code>
            if fallback:
                conforms_to.append(fallback)
    license_ = props.get_string(ctx, entity, "fr.aphp.healthdcat.license", title, dataproduct_urn, issues)
    is_referenced_by = props.get_strings(ctx, entity, "fr.aphp.healthdcat.isReferencedBy", title, dataproduct_urn, issues)

    number_of_records = props.get_int(entity, "fr.aphp.healthdcat.numberOfRecords", title, dataproduct_urn, issues)
    number_of_unique_individuals = props.get_int(entity, "fr.aphp.healthdcat.numberOfUniqueIndividuals", title, dataproduct_urn, issues)
    min_typical_age = props.get_int(entity, "fr.aphp.healthdcat.minTypicalAge", title, dataproduct_urn, issues)
    max_typical_age = props.get_int(entity, "fr.aphp.healthdcat.maxTypicalAge", title, dataproduct_urn, issues)
    population_coverage = props.get_string(ctx, entity, "fr.aphp.healthdcat.populationCoverage", title, dataproduct_urn, issues)
    provenance = props.get_string(ctx, entity, "fr.aphp.healthdcat.provenance", title, dataproduct_urn, issues)
    purpose = props.get_string(ctx, entity, "fr.aphp.healthdcat.purpose", title, dataproduct_urn, issues)

    issued_date = props.get_date(entity, "fr.aphp.healthdcat.issued", title, dataproduct_urn, issues)
    issued = datetime.combine(issued_date, datetime.min.time()) if issued_date else None
    modified = datetime.fromtimestamp(dp.lastModified.time / 1000) if getattr(dp, "lastModified", None) else None

    temporal_start = props.get_date(entity, "fr.aphp.healthdcat.temporalCoverageStart", title, dataproduct_urn, issues)
    temporal_end = props.get_date(entity, "fr.aphp.healthdcat.temporalCoverageEnd", title, dataproduct_urn, issues)
    temporal = PeriodOfTime(start_date=temporal_start, end_date=temporal_end) if (temporal_start or temporal_end) else None

    retention_start = props.get_date(entity, "fr.aphp.healthdcat.retentionPeriodStart", title, dataproduct_urn, issues)
    retention_end = props.get_date(entity, "fr.aphp.healthdcat.retentionPeriodEnd", title, dataproduct_urn, issues)
    retention_period = (
        PeriodOfTime(start_date=retention_start, end_date=retention_end) if (retention_start or retention_end) else None
    )

    # --- Agents (publisher / creator / hdab) — structured properties plates sur le DataProduct ---
    publisher = agents_reader.read_publisher(ctx, entity, title, dataproduct_urn, issues)
    creator = agents_reader.read_creator(ctx, entity, title, dataproduct_urn, issues)
    hdab = agents_reader.read_hdab(ctx, entity, title, dataproduct_urn, issues)
    contact_point = agents_reader.read_contact_point(ctx, entity, title, dataproduct_urn, issues)

    # --- Distributions / échantillons, depuis dataProductProperties.assets ---
    distributions = []
    samples = []
    for association in dp.assets or []:
        distribution = dataset_reader.read_distribution(ctx, association.destinationUrn, association.destinationUrn, title, issues)
        # dct:rights hérité de la licence du DataProduct (:healthDistribution_Shape l'exige =1)
        if distribution.rights is None and license_:
            distribution = _with_rights(distribution, license_)
        # dcatap:applicableLegislation hérité du DataProduct si l'asset n'en a pas
        if not distribution.applicable_legislation and applicable_legislation:
            distribution = _with_legislation(distribution, applicable_legislation)
        (samples if distribution.is_sample else distributions).append(distribution)

    return HealthDataset(
        source_urn=dataproduct_urn,
        dataset_id=dataset_id,
        identifier=f"{base_uri}/dataset/{dataset_id}",
        title=title,
        description=description,
        acronym=acronym,
        keywords=tuple(keywords),
        theme=(v.DATA_THEME_HEALTH,),
        dataset_type=dataset_type,
        access_rights=access_rights,
        applicable_legislation=applicable_legislation,
        language=language,
        publisher=publisher,
        creator=creator,
        contact_point=contact_point,
        hdab=hdab,
        provenance=provenance,
        purpose=purpose,
        legal_basis=legal_basis,
        personal_data=personal_data,
        health_category=health_category,
        health_theme=health_theme,
        spatial=tuple(spatial),
        number_of_records=number_of_records,
        number_of_unique_individuals=number_of_unique_individuals,
        min_typical_age=min_typical_age,
        max_typical_age=max_typical_age,
        population_coverage=population_coverage,
        retention_period=retention_period,
        coding_system=coding_system,
        issued=issued,
        modified=modified,
        temporal=temporal,
        accrual_periodicity=accrual_periodicity,
        conforms_to=tuple(c for c in conforms_to if c),
        license=license_,
        is_referenced_by=is_referenced_by,
        distributions=tuple(distributions),
        samples=tuple(samples),
        issues=issues,
    )


def _with_rights(distribution, rights: str):  # noqa: ANN001 - évite un import circulaire de Distribution ici
    from dataclasses import replace

    return replace(distribution, rights=rights)


def _with_legislation(distribution, legislation: tuple[str, ...]):  # noqa: ANN001
    from dataclasses import replace

    return replace(distribution, applicable_legislation=legislation)
