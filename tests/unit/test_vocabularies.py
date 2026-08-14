"""Résolution des vocabulaires contrôlés : succès et échec explicite (pas de
repli silencieux façon "NA"@en — voir mapping/vocabularies.py)."""

from __future__ import annotations

import pytest

from dh_healthdcat.mapping import vocabularies as v
from dh_healthdcat.model import ValidationIssue


def test_resolve_known_code():
    assert v.ACCESS_RIGHTS.resolve("PUBLIC") == "http://publications.europa.eu/resource/authority/access-right/PUBLIC"


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


def test_health_category_and_theme_use_hdh_dev_host():
    # Question ouverte Q1 de la spec : ne pas "corriger" cette URI par erreur.
    assert v.HEALTH_CATEGORY.resolve("HRAD").startswith("http://13.81.34.152:1101/")
