"""DataHub Dataset → Distribution / adms:sample (+ csvw:Table/Column).

Un asset devient un `adms:sample` plutôt qu'un `dcat:distribution` s'il porte
le tag `dcat:sample` (globalTags) — convention Phase 0, voir
`docs/mapping.md` §5.5. Sans ce tag, c'est une `dcat:distribution` normale,
avec les exigences SHACL plus strictes que cela implique (byteSize, format,
rights, applicableLegislation — voir mapping/distribution.py).
"""

from __future__ import annotations

from datetime import datetime, timezone

from dh_healthdcat.mapping import vocabularies as v
from dh_healthdcat.mapping.vocabularies import resolve_or_warn
from dh_healthdcat.model import Column, Distribution, Severity, Table, ValidationIssue
from dh_healthdcat.reader import props
from dh_healthdcat.reader.graph import ReadContext

SAMPLE_TAG_URN = "urn:li:tag:dcat:sample"


def _millis_to_datetime(millis: int | None) -> datetime | None:
    if not millis:
        return None
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc)


def is_sample_asset(ctx: ReadContext, dataset_urn: str) -> bool:
    entity = ctx.get_entity(dataset_urn)
    tags = entity.get("globalTags")
    if tags is None:
        return False
    return any(t.tag == SAMPLE_TAG_URN for t in tags.tags)


def _infer_format_code(dataset_name: str) -> str:
    """Dérive un code FileType à partir de l'extension du nom d'asset quand
    `fr.aphp.healthdcat.distributionFormat` n'est pas renseignée."""

    lowered = dataset_name.lower()
    for suffix, code in ((".ndjson", None), (".json", "JSON"), (".csv", "CSV"), (".parquet", "PARQUET"), (".xml", "XML")):
        if lowered.endswith(suffix):
            if code is None:
                return v.FILE_TYPE_NDJSON_FALLBACK  # NDJSON absent du vocabulaire HDH
            return code
    return "Other"  # clé exacte du vocabulaire FileType du HDH (pas "OTHER")


def _map_column(field) -> Column:  # noqa: ANN001 - SchemaFieldClass, typé côté acryl-datahub
    return Column(
        name=field.fieldPath,
        description=field.description,
        datatype=field.nativeDataType or "string",
        is_primary_key=bool(field.isPartOfKey),
    )


def read_distribution(
    ctx: ReadContext,
    dataset_urn: str,
    dataset_name: str,
    parent_dataset_name: str,
    issues: list[ValidationIssue],
) -> Distribution:
    """Traduit un Dataset DataHub (membre d'un DataProduct) en Distribution."""

    entity = ctx.get_entity(dataset_urn)
    dp = entity.get("datasetProperties")
    editable = entity.get("editableDatasetProperties")
    schema = entity.get("schemaMetadata")
    deprecation = entity.get("deprecation")

    # Le nom technique (segment "nom.qualifie" de l'URN, ex. "Patient.ndjson")
    # porte l'extension de fichier ; le displayName humain ("Patient (test...)")
    # ne l'a généralement pas. Les deux sont distincts : ne jamais inférer le
    # format depuis `title`, toujours depuis `technical_name` — bug réel
    # trouvé en testant contre une instance DataHub réelle, où `dp.name` était
    # un displayName sans extension et faisait systématiquement échouer la
    # détection de .ndjson/.csv/etc.
    technical_name = dataset_urn.rsplit(",", 2)[-2] if "," in dataset_urn else dataset_urn
    title = dp.name if dp and dp.name else technical_name
    description = (editable.description if editable and editable.description else None) or (
        dp.description if dp else None
    )

    access_url = props.get_string(ctx, entity, "fr.aphp.healthdcat.accessUrl", parent_dataset_name, dataset_urn, issues)
    if not access_url and dp and dp.externalUrl:
        access_url = dp.externalUrl
    download_url = props.get_string(ctx, entity, "fr.aphp.healthdcat.downloadUrl", parent_dataset_name, dataset_urn, issues)

    format_code = props.get_string(ctx, entity, "fr.aphp.healthdcat.distributionFormat", parent_dataset_name, dataset_urn, issues)
    if not format_code:
        format_code = _infer_format_code(technical_name)
        if format_code == v.FILE_TYPE_NDJSON_FALLBACK:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    dataset_name=parent_dataset_name,
                    dataset_urn=dataset_urn,
                    rdf_property="dct:format",
                    datahub_field="fr.aphp.healthdcat.distributionFormat",
                    message=f'".ndjson" absent du vocabulaire FileType du HDH — repli sur "{v.FILE_TYPE_NDJSON_FALLBACK}"',
                )
            )
    # resolve_or_warn plutôt que .resolve() : un code FileType invalide ne doit
    # pas faire planter tout l'export (P0-6) — trouvé en pratique via un bug de
    # casse ("OTHER" vs "Other") qui crashait ici avant ce garde-fou.
    format_uri = resolve_or_warn(
        v.FILE_TYPE,
        format_code,
        dataset_name=parent_dataset_name,
        dataset_urn=dataset_urn,
        datahub_field="fr.aphp.healthdcat.distributionFormat",
        issues=issues,
    )

    status_uri = None
    if deprecation is not None and deprecation.deprecated:
        status_uri = "http://publications.europa.eu/resource/authority/distribution-status/WITHDRAWN"

    table = None
    if schema is not None and schema.fields:
        table = Table(title=title, columns=tuple(_map_column(f) for f in schema.fields))

    is_sample = is_sample_asset(ctx, dataset_urn)

    # datasetProfile est un aspect timeseries (get_dataset_profile fait un appel
    # séparé de get_entity_semityped). Absence de profil -> byte_size reste
    # None ; mapping/distribution.py lève l'ERROR "dcat:byteSize manquant"
    # pour les dcat:distribution (pas les adms:sample, non concernées par
    # :healthDistribution_Shape) — pas la peine de dupliquer le signal ici.
    profile = ctx.get_dataset_profile(dataset_urn)
    byte_size = profile.sizeInBytes if profile is not None else None

    return Distribution(
        node_id=dataset_urn,
        title=title,
        is_sample=is_sample,
        description=description,
        access_url=access_url,
        download_url=download_url,
        format_uri=format_uri,
        byte_size=byte_size,
        rights=None,  # hérité au niveau DataProduct par l'appelant si besoin
        status_uri=status_uri,
        issued=_millis_to_datetime(dp.created.time if dp and dp.created else None),
        modified=_millis_to_datetime(dp.lastModified.time if dp and dp.lastModified else None),
        table=table,
        source_urn=dataset_urn,
    )
