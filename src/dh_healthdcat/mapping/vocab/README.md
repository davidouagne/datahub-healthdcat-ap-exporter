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

⚠️ `HealthCategories.yml` et `HealthTheme.yml` pointent sur un hôte de
développement en dur côté HDH (`http://13.81.34.152:1101/...`, vu tel quel dans
leurs fichiers sources). C'est la question ouverte **Q1** de la spec — à ne pas
considérer comme une erreur de recopie de notre part.

`LegalBasis.yml` est le seul fichier d'auteur (pas vendu) : il documente le
mapping des 12 codes `A6-1-*`/`A9-2-*` de la structured property
`fr.aphp.healthdcat.legalBasis` vers l'extension GDPR du Data Privacy
Vocabulary (`https://w3id.org/dpv/legal/eu/gdpr#`). Les 12 identifiants ont été
vérifiés terme à terme contre cette source le 2026-08-14 ; à revalider si le
DPV publie une nouvelle version majeure.
