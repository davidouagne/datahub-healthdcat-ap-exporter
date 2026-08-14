# Mapping DataHub ↔ HealthDCAT-AP

Documentation vivante du mapping implémenté par `src/dh_healthdcat/`. Reflète
le code réel, vérifié par `pyshacl` contre les shapes réelles du HDH
(`shapes/ehds/hdap-validator-sensitivity-shape.ttl`, copie conforme de
`hdh/catalogue-de-metadonnees/api/shacl-validator/validator/resources/ehds/shapes/hdap-validator-sensitivity-shape.ttl`).

## Principe

**DataProduct → `dcat:Dataset`.** Les Datasets DataHub membres deviennent
`dcat:distribution` (par défaut) ou `adms:sample` (s'ils portent le tag
`dcat:sample`). Leur `schemaMetadata` devient `csvw:Table`/`csvw:Column`.

## Espaces de noms (`mapping/namespaces.py`)

Alignés sur `queries.yaml:prefixes_ttl` côté HDH. `DCT` est un alias de
`rdflib.namespace.DCTERMS`.

## Correspondance DataProduct → `dcat:Dataset`

`M` = obligatoire (SHACL `sh:Violation`, `minCount ≥ 1`) · `R` = recommandé, non
vérifié par le SHACL de base · `⚙️` = dérivé/calculé, pas une saisie.

| Propriété | | Source DataHub | Module |
|---|---|---|---|
| `a dcat:Dataset, dcat:Resource` | ⚙️ | constante | dataset.py |
| `dct:identifier` (`xsd:anyURI`) | M | `{base_uri}/dataset/{dataProductKey.id}` | dataproduct.py |
| `dct:title` | M | `dataProductProperties.name` | dataproduct.py |
| `dct:description` | M | `dataProductProperties.description` | dataproduct.py |
| `dct:alternative` | | `fr.aphp.healthdcat.acronym` | |
| `dcat:keyword` | M | `globalTags` (hors `dcat:sample`) | |
| `dcat:theme` | M | constante `.../data-theme/HEAL` (voir note) | |
| `dct:type` | M, =1 | `fr.aphp.healthdcat.datasetType` → `DatasetType` | |
| `dct:accessRights` | M, =1 | `fr.aphp.healthdcat.accessRights` → `AccessRights` | |
| `dcatap:applicableLegislation` | M | `fr.aphp.healthdcat.applicableLegislation` → `ApplicableRegulations` | |
| `dct:publisher` | M, =1 | `fr.aphp.healthdcat.publisher{Name,Homepage,Email,Type,Note}`, `.trustedDataHolder` | agents.py |
| `dct:creator` | | `fr.aphp.healthdcat.creator{Name,Homepage,Email}` | agents.py |
| `dcat:contactPoint` | M | `fr.aphp.healthdcat.contactPoint{Name,Email,Url}` | agents.py |
| `healthdcatap:hdab` | M, =1 | `fr.aphp.healthdcat.hdab{Name,Homepage,Email}` | agents.py |
| `dct:provenance` | M | `fr.aphp.healthdcat.provenance` | |
| `dpv:hasPurpose` | M | `fr.aphp.healthdcat.purpose` | |
| `healthdcatap:healthCategory` | M | `fr.aphp.healthdcat.healthCategory` → `HealthCategories` | |
| `healthdcatap:healthTheme` | M | `fr.aphp.healthdcat.healthTheme` → `HealthTheme` | |
| `dct:spatial` | M | `fr.aphp.healthdcat.spatialCoverage` → `PublicationsEuropAuthorityCountry` ou passage direct | |
| `dcat:distribution` | M, ≥1 | assets non tagués `dcat:sample` | dataset.py (reader) |
| `adms:sample` | M, ≥1 | assets tagués `dcat:sample` | dataset.py (reader) |
| `dct:language` | | `fr.aphp.healthdcat.language` → `PublicationsEuropAuthorityLanguage` | |
| `dct:issued` | | `fr.aphp.healthdcat.issued` | |
| `dct:modified` | | `dataProductProperties.lastModified` | |
| `dct:temporal` | | `temporalCoverageStart`/`End` | |
| `dct:accrualPeriodicity` | | `publishingFrequency` → `Frequency` | |
| `dct:conformsTo` | | `referenceSpecification`, enveloppé en URI si nécessaire | |
| `dct:license` | | `license`, passage direct | |
| `dct:isReferencedBy` | | `fr.aphp.healthdcat.isReferencedBy` | |
| `healthdcatap:numberOfRecords`/`numberOfUniqueIndividuals`/`min|maxTypicalAge` | | `number` | |
| `healthdcatap:populationCoverage` | | `fr.aphp.healthdcat.populationCoverage` | |
| `healthdcatap:retentionPeriod` | | `retentionPeriodStart`/`End` → `dct:PeriodOfTime` | |
| `healthdcatap:hasCodingSystem` | | `coding` → `CodingSystem` (vocabulaire d'auteur) | |
| `dpv:hasLegalBasis` | | `legalBasis` → `LegalBasis` (vocabulaire d'auteur) | |
| `dpv:hasPersonalData` | | `fr.aphp.healthdcat.personalData` → `PersonalData` | |
| `foaf:page` | | `institutionalMemory.elements[].url` | non lu en v1 |
| `dqv:hasQualityAnnotation` | | entités `ASSERTION` | **P2, non implémenté** |

### Note — publisher / creator / hdab

Ces trois agents sont portés par des **structured properties plates,
directement sur le `DATA_PRODUCT`**, plutôt que par un CorpGroup référencé
via un `owner`. Contrainte du connecteur d'ingestion réellement utilisé côté
AP-HP (`aphp/datahub-yaml-source`) : il ne supporte ni `kind: CORP_GROUP` ni
`kind: OWNERSHIP_TYPE`, et n'interprète pas `type: urn:li:ownershipType:...`
dans `owners:` comme un type personnalisé — seul `structuredProperties:` sur
un document `DATA_PRODUCT` est fiable. `reader/agents.py` lit ces propriétés
directement sur l'entité DataProduct.

### Note — `dcat:theme`

v1 émet toujours et uniquement `.../data-theme/HEAL` (constante). Le HDH n'a
pas de vocabulaire `theme` dédié parmi ses 19 fichiers ; `HEAL` seul satisfait
déjà `dcat:theme minCount 1`. Aucune propriété `fr.aphp.healthdcat.theme`
n'est nécessaire tant qu'aucun besoin de thème secondaire n'est identifié.

## Correspondance Dataset DataHub → `dcat:Distribution` / `adms:sample`

`:healthDistribution_Shape` (étend `:Distribution_Shape`) n'impose ses
exigences renforcées **qu'aux `dcat:distribution`** — un `adms:sample` reste
valide avec la seule `dcat:accessURL`.

| Propriété | Distribution | Sample | Source |
|---|---|---|---|
| `dcat:accessURL` | M | M | `fr.aphp.healthdcat.accessUrl` (`entityTypes:[dataset]`), repli `datasetProperties.externalUrl` |
| `dcat:byteSize` (`xsd:nonNegativeInteger`) | M, =1 | — | `datasetProfile.sizeInBytes` (aspect **timeseries**, lu via `ReadContext.get_dataset_profile` → `graph.get_latest_timeseries_value`) |
| `dct:format` | M, =1 | — | `fr.aphp.healthdcat.distributionFormat`, sinon déduit de l'extension du **nom technique** du dataset (jamais du displayName, qui ne la porte pas) |
| `dct:rights` (nœud `dct:RightsStatement`, pas un littéral direct — exigé `sh:BlankNodeOrIRI`) | M, =1 | — | hérité de `fr.aphp.healthdcat.license` du DataProduct |
| `dcatap:applicableLegislation` | M | — | hérité du DataProduct si l'asset n'en a pas |
| `dct:title` / `dct:description` | | | `datasetProperties.name`/`.description`, fusion `editableDatasetProperties` |
| `csvw:Table` → `csvw:column` | | | `schemaMetadata.fields` |

## Vocabulaires (`mapping/vocab/`)

12 fichiers vendus tels quels depuis
`hdh/.../controlled_vocabulary/controled_voc_dicts/` (voir `vocab/README.md`
pour la liste et la procédure de resynchronisation), plus deux fichiers
d'auteur :

- **`LegalBasis.yml`** — mapping des 12 codes `eu-gdpr:A6-1-*`/`eu-gdpr:A9-2-*`
  vers l'extension GDPR du DPV (`https://w3id.org/dpv/legal/eu/gdpr#`).
- **`CodingSystem.yml`** — les 9 codes de `fr.aphp.healthdcat.coding`
  (SNOMED-CT, LOINC, ICD-10/11, ATC : URIs canoniques stables ; CIP13, UCD,
  CCAM, NFS : espace de noms `https://aphp.fr/codesystem/*` local et
  explicitement non déréférençable, faute d'identifiant officiel ANS/HDH).

Toute résolution échoue explicitement (`UnknownVocabularyValueError`) plutôt
que de retomber sur un `skos:prefLabel "NA"@en` silencieux comme le fait le
HDH à l'ingestion (`resolve()`) ; le reader dégrade ces échecs en
`Severity.WARNING` via `resolve_or_warn()`/`resolve_many_or_warn()` pour ne
pas faire échouer tout l'export d'un DataProduct par ailleurs valide.

## Extension `assets.yml` (Phase 0)

Voir le fichier lui-même (`aphp/datahub-sample/setup/assets.yml`) pour le
détail exact.

- **29 structured properties** `entityTypes:[dataProduct]` : les 12 portant
  l'identité du publisher/creator/hdab, plus identifiants, vocabulaires
  contrôlés, contact, dates, rétention (voir tableau ci-dessus).
- **4 structured properties** `entityTypes:[dataset]` : `accessUrl`,
  `downloadUrl`, `distributionFormat`, `distributionStatus`.
- **1 Tag** : `dcat:sample`, marque les assets à exporter en `adms:sample`
  plutôt qu'en `dcat:distribution`.

## Reste à faire

| Sujet | Portée | Priorité |
|---|---|---|
| `healthdcatap:analytics`, `healthdcatap:hasCodeValues` | Non exportés | P2 |
| `locn:address` (pays du HDAB) | `Agent.country` est lu et résolu mais jamais câblé dans `mapping/agent.py` (non exigé par le SHACL) | P2 |
| `prov:qualifiedAttribution` (dataController/dataProcessor) | Propriétés existantes non reprises, pas d'équivalent HealthDCAT-AP direct | P2 |
| `dqv:hasQualityAnnotation` | Entités `ASSERTION` (quality-layer) non lues | P2 |
| `fr.aphp.healthdcat.publishingFrequency` allowedValue `IRREGULAR` | Le vocabulaire HDH `Frequency` attend `IRREG` — écart détecté par `resolve_or_warn` (dégradé en avertissement, pas d'échec) | à corriger dans `assets.yml` |
| `HealthCategories`/`HealthTheme` (URIs HDH) | Pointent sur un hôte de développement en dur (`http://13.81.34.152:1101/...`) côté HDH | à reconfirmer avant publication en production |
| `fr.aphp.healthdcat.retentionPeriod` (ancienne, texte ISO 8601) | Dépréciée au profit de `retentionPeriodStart`/`retentionPeriodEnd`, toujours déclarée dans `assets.yml` mais plus exportée | à retirer une fois la curation terminée |
