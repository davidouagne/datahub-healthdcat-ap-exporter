"""Génère metadata.json, la partie du seed qu'aucun YAML natif ne couvre :
Datasets (propriétés, schéma, tags, SP), leur `datasetProfile` (timeseries,
source de `dcat:byteSize`) et les valeurs des SP du DataProduct.

Chargé ensuite par `datahub ingest` (source `file`). Le JSON est commité :
ce script ne sert qu'à le régénérer quand le seed change
(`uv run python tests/integration/seed/generate_metadata.py`).

Toutes les dates sont fixes : deux contrôles successifs doivent produire
des graphes isomorphes (#130).
"""

from __future__ import annotations

import json
from pathlib import Path

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    AuditStampClass,
    DatasetProfileClass,
    DatasetPropertiesClass,
    DomainPropertiesClass,
    GlobalTagsClass,
    OtherSchemaClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StringTypeClass,
    StructuredPropertiesClass,
    StructuredPropertyValueAssignmentClass,
    TagAssociationClass,
    TimeStampClass,
)

from dh_healthdcat import sp

DOMAIN_URN = "urn:li:domain:dhhc-verify"
DATAPRODUCT_URN = "urn:li:dataProduct:dhhc-verify-venues"
ASSET_URN = "urn:li:dataset:(urn:li:dataPlatform:s3,dhhc-verify/Patient.ndjson,PROD)"
SAMPLE_URN = "urn:li:dataset:(urn:li:dataPlatform:s3,dhhc-verify/Patient_sample.ndjson,PROD)"

CREATED_MS = 1_704_067_200_000  # 2024-01-01T00:00:00Z
MODIFIED_MS = 1_717_200_000_000  # 2024-06-01T00:00:00Z
ACTOR = "urn:li:corpuser:datahub"


def _sps(**values: str | float | list[str | float]) -> StructuredPropertiesClass:
    assignments = []
    for name, value in values.items():
        listed = value if isinstance(value, list) else [value]
        assignments.append(
            StructuredPropertyValueAssignmentClass(
                propertyUrn=f"urn:li:structuredProperty:{sp.qualified(name)}", values=listed
            )
        )
    return StructuredPropertiesClass(properties=assignments)


def _dataset(urn: str, name: str, description: str) -> list[MetadataChangeProposalWrapper]:
    return [
        MetadataChangeProposalWrapper(
            entityUrn=urn,
            aspect=DatasetPropertiesClass(
                name=name,
                description=description,
                created=TimeStampClass(time=CREATED_MS, actor=ACTOR),
                lastModified=TimeStampClass(time=MODIFIED_MS, actor=ACTOR),
            ),
        ),
        MetadataChangeProposalWrapper(
            entityUrn=urn,
            aspect=SchemaMetadataClass(
                schemaName=name,
                platform="urn:li:dataPlatform:s3",
                version=0,
                hash="",
                platformSchema=OtherSchemaClass(rawSchema=""),
                created=AuditStampClass(time=CREATED_MS, actor=ACTOR),
                lastModified=AuditStampClass(time=MODIFIED_MS, actor=ACTOR),
                fields=[
                    SchemaFieldClass(
                        fieldPath="id",
                        type=SchemaFieldDataTypeClass(type=StringTypeClass()),
                        nativeDataType="string",
                        description="Identifiant",
                        isPartOfKey=True,
                    ),
                    SchemaFieldClass(
                        fieldPath="gender",
                        type=SchemaFieldDataTypeClass(type=StringTypeClass()),
                        nativeDataType="string",
                        description="Sexe",
                    ),
                ],
            ),
        ),
    ]


def build() -> list[MetadataChangeProposalWrapper]:
    return [
        MetadataChangeProposalWrapper(
            entityUrn=DOMAIN_URN,
            aspect=DomainPropertiesClass(name="Contrôle Docker dh-healthdcat"),
        ),
        *_dataset(ASSET_URN, "Patient.ndjson", "Ressources FHIR Patient"),
        MetadataChangeProposalWrapper(
            entityUrn=ASSET_URN,
            aspect=_sps(
                accessUrl="https://s3.example.org/dhhc-verify/Patient.ndjson",
                distributionFormat="JSON",
                distributionStatus="COMPLETED",
            ),
        ),
        MetadataChangeProposalWrapper(
            entityUrn=ASSET_URN,
            aspect=DatasetProfileClass(
                timestampMillis=MODIFIED_MS, rowCount=1000, columnCount=2, sizeInBytes=123456
            ),
        ),
        *_dataset(SAMPLE_URN, "Patient_sample.ndjson", "Echantillon FHIR Patient"),
        MetadataChangeProposalWrapper(
            entityUrn=SAMPLE_URN,
            aspect=GlobalTagsClass(tags=[TagAssociationClass(tag="urn:li:tag:dcat:sample")]),
        ),
        MetadataChangeProposalWrapper(
            entityUrn=SAMPLE_URN,
            aspect=_sps(accessUrl="https://s3.example.org/dhhc-verify/Patient_sample.ndjson"),
        ),
        MetadataChangeProposalWrapper(
            entityUrn=DATAPRODUCT_URN,
            aspect=_sps(
                datasetType="PERSONAL_DATA",
                accessRights="NON_PUBLIC",
                applicableLegislation="COMMISSION IMPLEMENTING REGULATION (EU) 2023/138",
                healthCategory="HRAD",
                healthTheme="health_systems",
                spatialCoverage="FRA",
                provenance="Donnees issues du dossier patient informatise.",
                purpose="Recherche et pilotage de l'activite hospitaliere.",
                contactPointName="Coordination EDS",
                contactPointEmail="eds-coord@example.org",
                contactPointUrl="https://eds.example.org",
                license="https://eds.example.org/licence",
                referenceSpecification=["HL7-FHIR-R4", "OSIRIS"],
                isReferencedBy=["10.1234/abcd.2019", "https://hal.science/hal-04"],
                numberOfRecords=1000.0,
                publishingFrequency="DAILY",
                issued="2024-01-15",
                temporalCoverageStart="2015-01-01",
                temporalCoverageEnd="2023-12-31",
                publisherName="Etablissement de sante exemple",
                publisherHomepage="https://www.example.org",
                publisherEmail="eds-contact@example.org",
                publisherType="Hospital or Healthcare System",
                publisherNote="Entrepot de donnees de sante",
                trustedDataHolder="true",
                hdabName="Health Data Hub",
                hdabHomepage="https://health-data-hub.fr",
                hdabEmail="contact@health-data-hub.fr",
            ),
        ),
    ]


if __name__ == "__main__":
    # Même forme que le sink `file` de DataHub (liste d'objets MCP), écrite
    # directement : `write_metadata_file` prend un chemin Windows pour une URL.
    out = Path(__file__).with_name("metadata.json")
    payload = [mcp.to_obj(simplified_structure=True) for mcp in build()]
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
