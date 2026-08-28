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

⚠️ `HealthCategories.yml` et `HealthTheme.yml` résolvent vers
`http://healthdataportal.eu/resource/authority/{healthcategories,health-theme}/…`,
le namespace SEMIC HealthDCAT-AP (le même que `PublisherType.yml`). Aucun hôte
de vocabulaire **canonique** n'est publié à ce jour pour ces deux termes (le
vocabulaire HealthDCAT-AP `healthCategory` n'est pas encore créé côté EC ; le
Publications Office est pressenti à terme) — ces IRI ne sont donc pas encore
déréférençables. Ce n'est pas bloquant : la shape SHACL n'exige qu'une IRI
pour `healthdcatap:healthCategory`/`healthTheme` (`sh:nodeKind sh:BlankNodeOrIRI`,
aucun `sh:in`), donc l'hôte exact ne fait pas échouer la validation. Les
sources HDH portaient historiquement un hôte de dév en dur
(`http://13.81.34.152:1101/…`), repointé ici (issue #6) ; resynchroniser ces
deux fichiers quand un hôte officiel paraîtra.

Trois fichiers sont d'auteur (pas vendus du HDH, qui ne publie pas de
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
