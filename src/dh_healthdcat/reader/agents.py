"""structured properties du DataProduct → Agent / ContactPoint (modèle pivot).

`dct:publisher`, `dct:creator` et `healthdcatap:hdab` sont portés par des
structured properties **plates, directement sur le DataProduct**
(`fr.aphp.healthdcat.publisherName/.publisherHomepage/...`) — pas par un
CorpGroup référencé via un `ownershipType` personnalisé.

Ce choix n'est pas arbitraire : la première conception (CorpGroup +
`type: urn:li:ownershipType:healthdcat.publisher` dans `owners:`) s'est
révélée incompatible avec le connecteur d'ingestion réellement utilisé par
AP-HP (`aphp/datahub-yaml-source`). Son
`builders/common.py::build_ownership_aspect` écrit `owner.type` tel quel dans
le champ enum `OwnerClass.type`, sans jamais renseigner `typeUrn` — la
syntaxe `type: urn:li:ownershipType:...` n'y est pas interprétée comme un
type personnalisé (contrairement au SDK Python OSS `datahub dataproduct
upsert`, qui la supporte, lui). Par ailleurs, `kind: CORP_GROUP` et
`kind: OWNERSHIP_TYPE` n'existent tout simplement pas dans ce connecteur
(voir `ENTITY_DOC_TYPES_BY_KIND` dans `datahub_yaml_source/models.py`).

En revanche, `structuredProperties:` sur un document `DATA_PRODUCT` **est**
confirmé supporté (`builders/data_product.py::build_data_product`) — d'où
cette version plate, plus simple et surtout réellement chargeable.
"""

from __future__ import annotations

from dh_healthdcat.mapping import vocabularies as v
from dh_healthdcat.mapping.vocabularies import resolve_or_warn
from dh_healthdcat.model import Agent, ContactPoint, ValidationIssue
from dh_healthdcat.reader import props
from dh_healthdcat.reader.graph import ReadContext, SemitypedEntity


def _read_base_agent(
    ctx: ReadContext,
    entity: SemitypedEntity,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
    *,
    prefix: str,
) -> Agent | None:
    """Lit `fr.aphp.healthdcat.{prefix}Name/.{prefix}Homepage/.{prefix}Email`.
    Retourne None si aucune des trois n'est renseignée (rôle non utilisé sur
    ce DataProduct — ex. `dct:creator`, souvent absent)."""

    name = props.get_string(
        ctx, entity, f"fr.aphp.healthdcat.{prefix}Name", dataset_name, dataset_urn, issues
    )
    homepage = props.get_string(
        ctx, entity, f"fr.aphp.healthdcat.{prefix}Homepage", dataset_name, dataset_urn, issues
    )
    email = props.get_string(
        ctx, entity, f"fr.aphp.healthdcat.{prefix}Email", dataset_name, dataset_urn, issues
    )
    if not (name or homepage or email):
        return None
    return Agent(name=name or "", homepage=homepage or "", mbox=email or "")


def read_publisher(
    ctx: ReadContext,
    entity: SemitypedEntity,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> Agent | None:
    """dct:publisher → :HealthPublisherAgent_Shape.

    (publisherType / .Note / .trustedDataHolder en plus.)
    """

    agent = _read_base_agent(ctx, entity, dataset_name, dataset_urn, issues, prefix="publisher")
    if agent is None:
        return None

    publisher_type_code = props.get_string(
        ctx, entity, "fr.aphp.healthdcat.publisherType", dataset_name, dataset_urn, issues
    )
    publisher_type = resolve_or_warn(
        v.PUBLISHER_TYPE,
        publisher_type_code,
        dataset_name=dataset_name,
        dataset_urn=dataset_urn,
        datahub_field="fr.aphp.healthdcat.publisherType",
        issues=issues,
    )
    publisher_note = props.get_string(
        ctx, entity, "fr.aphp.healthdcat.publisherNote", dataset_name, dataset_urn, issues
    )
    trusted_data_holder = props.get_bool(
        entity, "fr.aphp.healthdcat.trustedDataHolder", dataset_name, dataset_urn, issues
    )

    return Agent(
        name=agent.name,
        homepage=agent.homepage,
        mbox=agent.mbox,
        publisher_type=publisher_type,
        publisher_note=publisher_note,
        trusted_data_holder=trusted_data_holder,
    )


def read_creator(
    ctx: ReadContext,
    entity: SemitypedEntity,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> Agent | None:
    """dct:creator → foaf:Agent simple (:Agent_Shape uniquement)."""

    return _read_base_agent(ctx, entity, dataset_name, dataset_urn, issues, prefix="creator")


def read_hdab(
    ctx: ReadContext,
    entity: SemitypedEntity,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> Agent | None:
    """healthdcatap:hdab → :HealthAgent_Shape (homepage et mbox obligatoires)."""

    return _read_base_agent(ctx, entity, dataset_name, dataset_urn, issues, prefix="hdab")


def read_contact_point(
    ctx: ReadContext,
    entity: SemitypedEntity,
    dataset_name: str,
    dataset_urn: str,
    issues: list[ValidationIssue],
) -> ContactPoint | None:
    """dcat:contactPoint — point de contact opérationnel, distinct du publisher."""

    name = props.get_string(
        ctx, entity, "fr.aphp.healthdcat.contactPointName", dataset_name, dataset_urn, issues
    )
    email = props.get_string(
        ctx, entity, "fr.aphp.healthdcat.contactPointEmail", dataset_name, dataset_urn, issues
    )
    if not name and not email:
        return None
    url = props.get_string(
        ctx, entity, "fr.aphp.healthdcat.contactPointUrl", dataset_name, dataset_urn, issues
    )
    return ContactPoint(name=name or dataset_name, email=email or "", url=url)
