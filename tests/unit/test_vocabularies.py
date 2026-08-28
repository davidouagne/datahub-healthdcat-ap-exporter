"""Résolution des vocabulaires contrôlés : succès et échec explicite (pas de
repli silencieux façon "NA"@en — voir mapping/vocabularies.py)."""

from __future__ import annotations

import pytest

from dh_healthdcat.mapping import vocabularies as v
from dh_healthdcat.model import ValidationIssue


def test_resolve_known_code():
    assert (
        v.ACCESS_RIGHTS.resolve("PUBLIC")
        == "http://publications.europa.eu/resource/authority/access-right/PUBLIC"
    )


def test_resolve_unknown_code_raises():
    with pytest.raises(v.UnknownVocabularyValueError):
        v.ACCESS_RIGHTS.resolve("NOPE")


def test_resolve_or_warn_degrades_gracefully():
    issues: list[ValidationIssue] = []
    result = v.resolve_or_warn(
        v.ACCESS_RIGHTS,
        "NOPE",
        dataset_name="Test",
        dataset_urn="urn:li:dataProduct:test",
        datahub_field="fr.aphp.healthdcat.accessRights",
        issues=issues,
    )
    assert result is None
    assert len(issues) == 1
    assert issues[0].datahub_field == "fr.aphp.healthdcat.accessRights"


def test_legal_basis_matches_dpv_gdpr_extension():
    # Clé "eu-gdpr:A9-2-j" : forme exacte stockée par fr.aphp.healthdcat.legalBasis
    # (assets.yml), pas l'identifiant DPV nu — voir vocab/README.md.
    assert v.LEGAL_BASIS.resolve("eu-gdpr:A9-2-j") == "https://w3id.org/dpv/legal/eu/gdpr#A9-2-j"


def test_reference_specification_maps_standards_to_canonical_uris():
    # Vocabulaire d'auteur (pas vendu du HDH) — URIs canoniques vérifiées le
    # 2026-08-28 contre les sources primaires (voir docs/research/
    # reference-specification-uris.md). OSIRIS n'y figure pas : il retombe sur
    # urn:aphp:conformsTo:OSIRIS côté reader.
    assert v.REFERENCE_SPECIFICATION.resolve("HL7-FHIR-R4") == "http://hl7.org/fhir/4.0.1"
    assert (
        v.REFERENCE_SPECIFICATION.resolve("OMOP-CDM-5.4")
        == "https://ohdsi.github.io/CommonDataModel/cdm54.html"
    )
    assert v.REFERENCE_SPECIFICATION.resolve("HL7v2") == "urn:hl7-org:v2xml"
    with pytest.raises(v.UnknownVocabularyValueError):
        v.REFERENCE_SPECIFICATION.resolve("OSIRIS")


def test_health_category_and_theme_use_semic_authority_host():
    # Aucun hôte de vocab canonique n'existe encore pour healthCategory /
    # healthTheme (vocab HealthDCAT-AP non publié). On aligne sur le namespace
    # SEMIC healthdataportal.eu, comme PublisherType.yml — non déréférençable
    # pour l'instant, mais un identifiant SEMIC plutôt qu'une IP de dev.
    assert (
        v.HEALTH_CATEGORY.resolve("HRAD")
        == "http://healthdataportal.eu/resource/authority/healthcategories/HRAD"
    )
    assert (
        v.HEALTH_THEME.resolve("health_systems")
        == "http://healthdataportal.eu/resource/authority/health-theme/HEALTH_SYSTEMS"
    )
