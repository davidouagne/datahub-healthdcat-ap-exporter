"""Résolution des vocabulaires contrôlés : code court DataHub → URI d'autorité.

Les fichiers sous `vocab/*.yml` sont soit vendus depuis le HDH, soit (pour
`LegalBasis`) documentés par nos soins — voir `vocab/README.md` pour le détail
et les mises en garde (notamment Q1 : `HealthCategories`/`HealthTheme`
pointent sur un hôte de développement HDH en dur).

`resolve()` échoue fort sur un code inconnu plutôt que de retomber sur un
`skos:prefLabel "NA"@en` silencieux comme le fait le HDH à l'ingestion : notre
rôle est justement de détecter ces écarts avant l'envoi (P0-10).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from dh_healthdcat.model import ValidationIssue

VOCAB_DIR = Path(__file__).parent / "vocab"


class UnknownVocabularyValueError(ValueError):
    """Levée quand un code DataHub ne correspond à aucune valeur autorisée."""

    def __init__(self, vocabulary: str, code: str, valid_codes: list[str]) -> None:
        self.vocabulary = vocabulary
        self.code = code
        self.valid_codes = valid_codes
        sample = ", ".join(sorted(valid_codes)[:10])
        more = f" (+{len(valid_codes) - 10} autres)" if len(valid_codes) > 10 else ""
        super().__init__(
            f'valeur "{code}" absente du vocabulaire {vocabulary}. '
            f"Valeurs attendues : {sample}{more}."
        )


@dataclass(frozen=True, slots=True)
class Vocabulary:
    name: str
    code_to_uri: dict[str, str]
    labels_fr: dict[str, str]

    def resolve(self, code: str) -> str:
        try:
            return self.code_to_uri[code]
        except KeyError:
            raise UnknownVocabularyValueError(
                self.name, code, list(self.code_to_uri)
            ) from None

    def resolve_optional(self, code: str | None) -> str | None:
        return None if code is None else self.resolve(code)

    def label(self, code: str, default: str | None = None) -> str:
        return self.labels_fr.get(code, default if default is not None else code)


@lru_cache(maxsize=None)
def _load(name: str) -> Vocabulary:
    path = VOCAB_DIR / f"{name}.yml"
    if not path.exists():
        raise FileNotFoundError(
            f"Vocabulaire '{name}' introuvable ({path}). "
            "Vérifier mapping/vocab/README.md pour la liste vendue."
        )
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    body = data[name]
    return Vocabulary(
        name=name,
        code_to_uri=dict(body["vocabulary_list"]),
        labels_fr=dict(body.get("fr", {})),
    )


# --- Vocabulaires utilisés par le mapping DataProduct → dcat:Dataset ---------

ACCESS_RIGHTS = _load("AccessRights")
DATASET_TYPE = _load("DatasetType")
FREQUENCY = _load("Frequency")
HEALTH_CATEGORY = _load("HealthCategories")
HEALTH_THEME = _load("HealthTheme")
PERSONAL_DATA = _load("PersonalData")
PUBLISHER_TYPE = _load("PublisherType")
BOOLEANS = _load("Booleans")
APPLICABLE_REGULATIONS = _load("ApplicableRegulations")
FILE_TYPE = _load("FileType")
LANGUAGE = _load("PublicationsEuropAuthorityLanguage")
COUNTRY = _load("PublicationsEuropAuthorityCountry")
LEGAL_BASIS = _load("LegalBasis")
CODING_SYSTEM = _load("CodingSystem")

# dcat:theme n'a pas de dictionnaire dédié côté HDH (PublicationsEuropAuthorityTheme
# existe mais sert au thème générique EU) ; HealthDCAT-AP impose la valeur HEAL a
# minima. On l'expose en constante plutôt qu'en vocabulaire à un seul code.
DATA_THEME_HEALTH = "http://publications.europa.eu/resource/authority/data-theme/HEAL"

# NDJSON n'existe pas dans le vocabulaire FileType du HDH (vérifié : absent des
# ~200 codes). C'est le format de sortie de la sharing-layer AP-HP
# (`sharing_layer_Patient.ndjson`). Faute de code dédié, on retombe sur JSON
# avec un avertissement — voir reader/dataset.py.
FILE_TYPE_NDJSON_FALLBACK = "JSON"


def resolve_or_warn(
    vocab: Vocabulary,
    code: str | None,
    *,
    dataset_name: str,
    dataset_urn: str,
    datahub_field: str,
    issues: list["ValidationIssue"],
) -> str | None:
    """`vocab.resolve(code)`, mais un code inconnu devient un WARNING dans
    `issues` (pas une exception) : un seul code hors vocabulaire ne doit pas
    faire échouer tout l'export d'un DataProduct par ailleurs valide (G4)."""

    if code is None:
        return None
    from dh_healthdcat.model import Severity, ValidationIssue as VI

    try:
        return vocab.resolve(code)
    except UnknownVocabularyValueError as exc:
        issues.append(
            VI(
                severity=Severity.WARNING,
                dataset_name=dataset_name,
                dataset_urn=dataset_urn,
                rdf_property="(vocabulaire)",
                datahub_field=datahub_field,
                message=str(exc),
            )
        )
        return None


def resolve_many_or_warn(
    vocab: Vocabulary,
    codes: tuple[str, ...],
    *,
    dataset_name: str,
    dataset_urn: str,
    datahub_field: str,
    issues: list["ValidationIssue"],
) -> tuple[str, ...]:
    resolved = (
        resolve_or_warn(vocab, code, dataset_name=dataset_name, dataset_urn=dataset_urn, datahub_field=datahub_field, issues=issues)
        for code in codes
    )
    return tuple(r for r in resolved if r is not None)
