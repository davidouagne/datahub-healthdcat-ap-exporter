# Vocabulaires contrôlés

La plupart des fichiers de ce dossier sont une copie conforme (vendue) des
dictionnaires de vocabulaire du catalogue HDH :

`hdh/catalogue-de-metadonnees/api/app/tableur_rdf_extractor/controlled_vocabulary/controled_voc_dicts/`

Ils sont dupliqués ici plutôt que référencés par chemin pour que ce dépôt reste
autonome (pas de dépendance de build sur un autre dépôt AP-HP). **En cas de
divergence constatée avec le HDH, le HDH fait foi** — resynchroniser ces
fichiers, pas l'inverse.

Fichiers vendus : `AccessRights`, `ApplicableRegulations`, `Booleans`,
`DatasetType`, `FileType`, `Frequency`, `HealthCategories`, `HealthTheme`,
`PersonalData`, `PublicationsEuropAuthorityCountry`,
`PublicationsEuropAuthorityLanguage`, `PublisherType`.

⚠️ Écarts connus entre ces fichiers vendus et la spec HealthDCAT-AP/DPV
officielle (namespace `PersonalData.yml`, terme `Death` sans équivalent DPV,
hôte `HealthCategories`/`HealthTheme` non canonique) : consolidés dans
[`docs/research/hdh-healthdcat-ap-gaps.md`](../../../../docs/research/hdh-healthdcat-ap-gaps.md),
avec la politique appliquée (ne jamais corriger un fichier vendu localement,
signaler au HDH). Un seul de ces écarts est corrigé ici (le repoint d'hôte
`HealthCategories`/`HealthTheme`, issue #6, antérieur à cette politique).

Quatre fichiers sont d'auteur (pas vendus du HDH, qui ne publie pas de
dictionnaire équivalent) :

- `LegalBasis.yml` : mapping des 12 codes `A6-1-*`/`A9-2-*` de
  `fr.aphp.healthdcat.legalBasis` vers l'extension GDPR du Data Privacy
  Vocabulary (`https://w3id.org/dpv/legal/eu/gdpr#`). Les 12 identifiants ont
  été vérifiés terme à terme contre cette source le 2026-08-14 ; à revalider si
  le DPV publie une nouvelle version majeure.
- `CodingSystem.yml` : les 9 codes de `fr.aphp.healthdcat.coding` (URIs
  canoniques HL7/OMS/WHO-CC stables ; `CIP13`/`UCD`/`CCAM`/`NFS` en espace de
  noms AP-HP local non déréférençable, faute d'identifiant officiel ANS/HDH).
- `ReferenceSpecification.yml` : `HL7-FHIR-R4` / `OMOP-CDM-5.4` / `HL7v2` de
  `fr.aphp.healthdcat.referenceSpecification` (→ `dct:conformsTo`) vers leurs
  URIs canoniques, vérifiées contre les sources primaires le 2026-08-28 (voir
  `docs/research/reference-specification-uris.md`). Tout autre code (p. ex.
  `OSIRIS`) retombe sur `urn:aphp:conformsTo:<code>` côté
  `reader/dataproduct.py`.
- `DistributionStatus.yml` : `COMPLETED` / `WITHDRAWN` de
  `fr.aphp.healthdcat.distributionStatus` (→ `adms:status`) vers le NAL EU
  Publications Office `.../distribution-status/*` (sous-ensemble retenu par le
  registre). Câblé dans `reader/dataset.py` ; une dépréciation DataHub écrase
  en `WITHDRAWN`.
