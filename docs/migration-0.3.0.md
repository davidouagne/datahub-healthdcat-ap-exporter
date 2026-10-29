# Migrer vers dh-healthdcat 0.3.0

La 0.3.0 rend l'exporteur générique (ADR-0005) : elle regroupe tous ses changements
cassants dans une seule version, avec un seul guide. Ce guide s'adresse à un adoptant qui
exporte déjà avec la 0.2.x, c'est-à-dire aujourd'hui l'AP-HP.

## En bref

| Changement | Ce qu'il faut faire |
|---|---|
| Les structured properties passent de `fr.aphp.healthdcat.*` à `healthdcatap.*` ; l'ancien préfixe n'est plus lu | Créer les nouvelles définitions, recopier les valeurs, puis supprimer les anciennes (§ 1) |
| L'URI de base n'a plus de valeur par défaut (`https://eds.aphp.fr`) | La déclarer dans le profil ou par `--base-uri` (§ 2) |
| Un code `referenceSpecification` non résolu devient `<URI de base>/conformsTo/<code>` au lieu de `urn:aphp:conformsTo:<code>` | Rien, sauf si un consommateur s'appuie sur l'ancienne IRI (§ 3) |
| `acryl-datahub>=1.7,<1.8` : seul un serveur DataHub 1.7.x est vérifié | Vérifier la version du serveur (§ 4) |

L'ordre compte : les nouvelles SP doivent porter leurs valeurs **avant** la montée de
version, sinon la 0.3.0 s'arrête au lancement (voir § 1, étape 5).

## 1. Renommer les structured properties

Les noms locaux ne changent pas : seul le préfixe change. DataHub ne sait pas renommer une
structured property ; la migration crée donc les nouvelles à côté des anciennes, y recopie
les valeurs, puis supprime les anciennes.

1. **Générer et appliquer les nouvelles définitions**, avec la 0.3.0 installée dans un
   environnement à part (elle n'écrit jamais dans DataHub) :

   ```bash
   dh-healthdcat properties --output structured-properties.yml
   datahub properties upsert -f structured-properties.yml
   ```

   Les définitions publiées par ce dépôt autorisent toutes les valeurs que l'exporteur sait
   résoudre : elles peuvent être plus larges que celles de votre registre.

2. **Recopier les valeurs** sous les nouveaux noms, en réingérant depuis votre source avec
   les clés renommées selon la table ci-dessous. À l'AP-HP : renommer les clés dans le
   registre et dans les `assets.yml` lus par `datahub-yaml-source`, puis relancer
   l'ingestion.

3. **Vérifier** avec la 0.3.0 : sur une instance qui porte les deux préfixes, seul
   `healthdcatap.*` est lu. Un `export-file` doit donner les mêmes jeux qu'avec la 0.2.x,
   aux différences des § 2 et 3 près.

4. **Monter de version** l'exporteur utilisé en production.

5. **Supprimer les anciennes définitions** une fois la 0.2.x retirée :

   ```bash
   grep '^- id:' structured-properties.yml \
     | sed 's/^- id: healthdcatap\./urn:li:structuredProperty:fr.aphp.healthdcat./' \
     > anciennes-sp.txt
   datahub delete --urn-file anciennes-sp.txt --hard
   ```

Si la 0.3.0 tourne sur une instance qui ne définit que l'ancien préfixe, elle s'arrête au
lancement avec une seule erreur qui renvoie à ce guide, au lieu d'exclure chaque jeu pour
propriétés manquantes.

### Table de correspondance

Générée à partir des définitions canoniques (`src/dh_healthdcat/sp_definitions.yml`) ; un
test vérifie qu'elle leur correspond.

| Ancien nom | Nouveau nom | Type | Cardinalité | Entités |
|---|---|---|---|---|
| `fr.aphp.healthdcat.acronym` | `healthdcatap.acronym` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.datasetType` | `healthdcatap.datasetType` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.healthCategory` | `healthdcatap.healthCategory` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.healthTheme` | `healthdcatap.healthTheme` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.isReferencedBy` | `healthdcatap.isReferencedBy` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.issued` | `healthdcatap.issued` | date | SINGLE | dataProduct |
| `fr.aphp.healthdcat.language` | `healthdcatap.language` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.publishingFrequency` | `healthdcatap.publishingFrequency` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.maxTypicalAge` | `healthdcatap.maxTypicalAge` | number | SINGLE | dataProduct |
| `fr.aphp.healthdcat.minTypicalAge` | `healthdcatap.minTypicalAge` | number | SINGLE | dataProduct |
| `fr.aphp.healthdcat.numberOfRecords` | `healthdcatap.numberOfRecords` | number | SINGLE | dataProduct |
| `fr.aphp.healthdcat.numberOfUniqueIndividuals` | `healthdcatap.numberOfUniqueIndividuals` | number | SINGLE | dataProduct |
| `fr.aphp.healthdcat.populationCoverage` | `healthdcatap.populationCoverage` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.spatialCoverage` | `healthdcatap.spatialCoverage` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.temporalCoverageEnd` | `healthdcatap.temporalCoverageEnd` | date | SINGLE | dataProduct |
| `fr.aphp.healthdcat.temporalCoverageStart` | `healthdcatap.temporalCoverageStart` | date | SINGLE | dataProduct |
| `fr.aphp.healthdcat.applicableLegislation` | `healthdcatap.applicableLegislation` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.legalBasis` | `healthdcatap.legalBasis` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.personalData` | `healthdcatap.personalData` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.purpose` | `healthdcatap.purpose` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.retentionPeriodEnd` | `healthdcatap.retentionPeriodEnd` | date | SINGLE | dataProduct |
| `fr.aphp.healthdcat.retentionPeriodStart` | `healthdcatap.retentionPeriodStart` | date | SINGLE | dataProduct |
| `fr.aphp.healthdcat.coding` | `healthdcatap.coding` | string | MULTIPLE | dataProduct |
| `fr.aphp.healthdcat.provenance` | `healthdcatap.provenance` | rich_text | SINGLE | dataProduct |
| `fr.aphp.healthdcat.referenceSpecification` | `healthdcatap.referenceSpecification` | string | MULTIPLE | dataset, dataProduct |
| `fr.aphp.healthdcat.accessRights` | `healthdcatap.accessRights` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.accessUrl` | `healthdcatap.accessUrl` | string | SINGLE | dataset |
| `fr.aphp.healthdcat.distributionFormat` | `healthdcatap.distributionFormat` | string | SINGLE | dataset |
| `fr.aphp.healthdcat.distributionStatus` | `healthdcatap.distributionStatus` | string | SINGLE | dataset |
| `fr.aphp.healthdcat.downloadUrl` | `healthdcatap.downloadUrl` | string | SINGLE | dataset |
| `fr.aphp.healthdcat.license` | `healthdcatap.license` | string | SINGLE | dataset, dataProduct |
| `fr.aphp.healthdcat.contactPointEmail` | `healthdcatap.contactPointEmail` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.contactPointName` | `healthdcatap.contactPointName` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.contactPointUrl` | `healthdcatap.contactPointUrl` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.creatorEmail` | `healthdcatap.creatorEmail` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.creatorHomepage` | `healthdcatap.creatorHomepage` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.creatorName` | `healthdcatap.creatorName` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.publisherEmail` | `healthdcatap.publisherEmail` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.publisherHomepage` | `healthdcatap.publisherHomepage` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.publisherName` | `healthdcatap.publisherName` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.publisherNote` | `healthdcatap.publisherNote` | rich_text | SINGLE | dataProduct |
| `fr.aphp.healthdcat.publisherType` | `healthdcatap.publisherType` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.hdabEmail` | `healthdcatap.hdabEmail` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.hdabHomepage` | `healthdcatap.hdabHomepage` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.hdabName` | `healthdcatap.hdabName` | string | SINGLE | dataProduct |
| `fr.aphp.healthdcat.trustedDataHolder` | `healthdcatap.trustedDataHolder` | string | SINGLE | dataProduct |

## 2. Déclarer l'URI de base

L'URI de base est l'espace de noms HTTP de l'adoptant : l'exporteur y forge `dct:identifier`
(`<base>/dataset/<id>`) et le repli `dct:conformsTo` (§ 3). Elle n'a plus de valeur par
défaut ; sans elle, `export-file` et `push-hdh` s'arrêtent avant tout appel réseau
(code 2). La déclarer dans le profil du fichier de configuration :

```yaml
profiles:
  prod:
    url: https://catalogue.health-data-hub.fr
    base_uri: https://eds.aphp.fr
```

ou la passer à chaque appel avec `--base-uri`, qui l'emporte sur le profil.
`export-file` accepte désormais `--config` et `--profile`, comme `push-hdh`.

Pour que les `dct:identifier` déjà publiés ne changent pas, déclarer l'ancienne valeur
par défaut : `https://eds.aphp.fr` pour l'AP-HP.

## 3. Repli `dct:conformsTo`

Un code de `referenceSpecification` absent du vocabulaire (par exemple `OSIRIS`) devenait
`urn:aphp:conformsTo:<code>`. Il devient `<URI de base>/conformsTo/<code>`, par exemple
`https://eds.aphp.fr/conformsTo/OSIRIS`. Les codes du vocabulaire (`HL7-FHIR-R4`,
`OMOP-CDM-5.4`, `HL7v2`) ne changent pas. Les jeux repoussés au HDH portent la nouvelle IRI.

## 4. Version du serveur DataHub

La 0.3.0 dépend de `acryl-datahub>=1.7,<1.8` : seule la série 1.7 du serveur est
vérifiée (ADR-0004). Hors de cette plage, `export-file` et `push-hdh` avertissent et
continuent ; `--strict-version` les fait échouer. Python 3.11 reste le minimum.

## Autres évolutions de sortie (non cassantes)

Elles changent le Turtle produit sans demander d'action :

- `dct:modified` est émis : la plus récente modification des distributions.
- `dcat:landingPage` (lien externe du DataProduct) et `foaf:page` (liens de
  documentation) sont émis. Le Catalogue HDH ne les conserve pas à l'ingestion
  (`docs/research/hdh-healthdcat-ap-gaps.md`).
- Un asset partagé entre deux DataProducts reçoit un nœud de distribution par
  DataProduct, et un avertissement le signale.
- Si un DataProduct déclare des output ports, seuls ces ports deviennent des
  distributions (ADR-0006). Sans port déclaré, rien ne change.
