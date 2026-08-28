# datahub-healthdcat-ap-exporter

Traduit les métadonnées d'un catalogue DataHub en RDF HealthDCAT-AP, pour un fichier
Turtle ou l'API du Catalogue de métadonnées du Health Data Hub (HDH).

## Langage

### Côté DataHub

**DataProduct**:
L'entité DataHub qui devient un `dcat:Dataset`. La racine de chaque graphe produit.
_Avoid_: dataset (réservé à `dcat:Dataset`), jeu de données

**Asset**:
Un Dataset DataHub membre d'un DataProduct. Devient une `dcat:distribution`, ou un
`adms:sample` s'il porte le tag `dcat:sample`.
_Avoid_: distribution (c'est la sortie, pas la source), fichier

**Structured property (SP)**:
Un champ typé `fr.aphp.healthdcat.*` porté par un DataProduct ou un asset, contenant une
valeur HealthDCAT-AP (code de vocabulaire, date, texte). Seule forme d'extension fiable
avec le connecteur d'ingestion AP-HP.
_Avoid_: custom property, propriété personnalisée, tag

### Côté HealthDCAT-AP / RDF

**Modèle pivot**:
Les dataclasses (`HealthDataset`, `Distribution`, …) qui portent uniquement des valeurs
déjà résolues, entre le reader DataHub et le mapping RDF. Ne connaît ni DataHub ni RDF.
_Avoid_: DTO, représentation intermédiaire, modèle interne

**Vocabulaire d'auteur**:
Un fichier `mapping/vocab/*.yml` écrit par ce projet (pas repris du HDH), mappant des
codes courts vers des URIs d'autorité.
_Avoid_: custom vocab, vocabulaire local

**Vocabulaire vendu**:
Un fichier `mapping/vocab/*.yml` copié verbatim des dictionnaires du Catalogue HDH. En cas
de divergence, le HDH fait foi.
_Avoid_: vocabulaire importé, vocabulaire miroir

**HDAB**:
Health Data Access Body au sens EHDS ; porté par `healthdcatap:hdab`.
_Avoid_: organisme d'accès, autorité EHDS

### Profils & validation

**Sensitivity shape**:
`shapes/ehds/hdap-validator-sensitivity-shape.ttl` — la shape SHACL qu'applique le
validateur du Catalogue HDH (profil EHDS données sensibles). C'est la porte du CI.
_Avoid_: shape HDH, fichier SHACL, validateur

**R7**:
HealthDCAT-AP Release 7 (brouillon EC, 2026-05), le profil cible « officiel ». Sa SHACL
diverge de la sensitivity shape sur ~30 termes.
_Avoid_: profil officiel, spec EC

**Écart R7 résiduel**:
Un endroit où la sortie satisfait la sensitivity shape (donc le CI) mais pas R7, écart
accepté délibérément et consigné (voir `docs/adr/`).
_Avoid_: divergence, non-conformité, bug
