"""Lecture des structured properties d'une entité, avec coercition tolérante.

`PrimitivePropertyValue` (le type PDL sur le fil) n'est qu'une union
`string | double` — une propriété déclarée `number` ou `date` peut donc
arriver en chaîne (cas avéré sur `fr.aphp.healthdcat.numberOfRecords`,
stocké `"1000000000"` dans dataproduct-layer/assets.yml). Ce module coerce
selon la *définition* de la propriété (résolue une fois via
`ReadContext.property_definitions`), pas selon le type Python reçu, et
journalise un avertissement dans `issues` en cas d'écart (P0-3).
"""

from __future__ import annotations

from datetime import date, datetime

from dh_healthdcat.model import Severity, ValidationIssue
from dh_healthdcat.reader.graph import ReadContext, SemitypedEntity

STRING = "urn:li:dataType:datahub.string"
RICH_TEXT = "urn:li:dataType:datahub.rich_text"
NUMBER = "urn:li:dataType:datahub.number"
DATE = "urn:li:dataType:datahub.date"
URN = "urn:li:dataType:datahub.urn"

STRUCTURED_PROPERTY_PREFIX = "urn:li:structuredProperty:"


def _warn(issues: list[ValidationIssue], dataset_name: str, dataset_urn: str, field: str, message: str) -> None:
    issues.append(
        ValidationIssue(
            severity=Severity.WARNING,
            dataset_name=dataset_name,
            dataset_urn=dataset_urn,
            rdf_property="(coercition)",
            datahub_field=field,
            message=message,
        )
    )


def raw_values(entity: SemitypedEntity, qualified_name: str) -> list[str | float]:
    """Valeurs brutes (non coercées) d'une structured property sur une entité,
    ou `[]` si absente."""

    aspect = entity.get("structuredProperties")
    if aspect is None:
        return []
    target_urn = STRUCTURED_PROPERTY_PREFIX + qualified_name
    values: list[str | float] = []
    for assignment in aspect.properties:
        if assignment.propertyUrn == target_urn:
            values.extend(assignment.values)
    return values


def _coerce_str(
    ctx: ReadContext,
    values: list[str | float],
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> list[str]:
    out: list[str] = []
    for v in values:
        if isinstance(v, str):
            out.append(v)
        else:
            out.append(str(v))
            _warn(issues, dataset_name, dataset_urn, qualified_name, f"attendu texte, reçu nombre ({v!r}) — converti tel quel")
    return out


def _coerce_int(
    values: list[str | float],
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> list[int]:
    out: list[int] = []
    for v in values:
        if isinstance(v, str):
            try:
                out.append(int(float(v)))
                _warn(issues, dataset_name, dataset_urn, qualified_name, f"attendu nombre, reçu texte ({v!r}) — converti")
            except ValueError:
                _warn(issues, dataset_name, dataset_urn, qualified_name, f"valeur non numérique ignorée ({v!r})")
        else:
            out.append(int(v))
    return out


def _coerce_date(
    values: list[str | float],
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> list[date]:
    out: list[date] = []
    for v in values:
        text = str(v)
        try:
            out.append(date.fromisoformat(text[:10]))
        except ValueError:
            _warn(issues, dataset_name, dataset_urn, qualified_name, f"date non ISO-8601 ignorée ({text!r})")
    return out


def _coerce_bool(
    values: list[str | float],
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> list[bool]:
    out: list[bool] = []
    for v in values:
        text = str(v).strip().lower()
        if text in ("true", "1"):
            out.append(True)
        elif text in ("false", "0"):
            out.append(False)
        else:
            _warn(issues, dataset_name, dataset_urn, qualified_name, f"booléen non reconnu ignoré ({v!r})")
    return out


def get_strings(
    ctx: ReadContext,
    entity: SemitypedEntity,
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> tuple[str, ...]:
    """Toutes les valeurs (string/urn/rich_text), coercées en texte."""

    values = raw_values(entity, qualified_name)
    return tuple(_coerce_str(ctx, values, qualified_name, dataset_name, dataset_urn, issues))


def get_string(
    ctx: ReadContext,
    entity: SemitypedEntity,
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> str | None:
    values = get_strings(ctx, entity, qualified_name, dataset_name, dataset_urn, issues)
    return values[0] if values else None


def get_ints(
    entity: SemitypedEntity,
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> tuple[int, ...]:
    values = raw_values(entity, qualified_name)
    return tuple(_coerce_int(values, qualified_name, dataset_name, dataset_urn, issues))


def get_int(
    entity: SemitypedEntity,
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> int | None:
    values = get_ints(entity, qualified_name, dataset_name, dataset_urn, issues)
    return values[0] if values else None


def get_dates(
    entity: SemitypedEntity,
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> tuple[date, ...]:
    values = raw_values(entity, qualified_name)
    return tuple(_coerce_date(values, qualified_name, dataset_name, dataset_urn, issues))


def get_date(
    entity: SemitypedEntity,
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> date | None:
    values = get_dates(entity, qualified_name, dataset_name, dataset_urn, issues)
    return values[0] if values else None


def get_bool(
    entity: SemitypedEntity,
    qualified_name: str,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> bool | None:
    values = raw_values(entity, qualified_name)
    coerced = _coerce_bool(values, qualified_name, dataset_name, dataset_urn, issues)
    return coerced[0] if coerced else None
