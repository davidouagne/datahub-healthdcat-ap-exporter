# Mapping DataHub ↔ HealthDCAT-AP

Documentation vivante du mapping implémenté par `src/dh_healthdcat/`. Reflète
le code réel, vérifié par `pyshacl` contre les shapes réelles du HDH
(`shapes/ehds/hdap-validator-sensitivity-shape.ttl`, copie conforme de
`hdh/catalogue-de-metadonnees/api/shacl-validator/validator/resources/ehds/shapes/hdap-validator-sensitivity-shape.ttl`).

## Principe

**DataProduct → `dcat:Dataset`.** Les Datasets DataHub membres deviennent
`dcat:distribution` (par défaut) ou `adms:sample` (s'ils portent le tag
`dcat:sample`). Leur `schemaMetadata` devient `csvw:Table`/`csvw:Column`.
Si le DataProduct déclare au moins un **output port** (`outputPort` de
l'association), seuls les ports deviennent des `dcat:distribution` ; les autres
assets sont ignorés, sauf les échantillons tagués `dcat:sample` (ADR-0006).

## Espaces de noms (`mapping/namespaces.py`)

Alignés sur `queries.yaml:prefixes_ttl` côté HDH. `DCT` est un alias de
`rdflib.namespace.DCTERMS`.

## Correspondance DataProduct → `dcat:Dataset`

`M` = obligatoire (SHACL `sh:Violation`, `minCount ≥ 1`) · `R` = recommandé, non
vérifié par le SHACL de base · `⚙️` = dérivé/calculé, pas une saisie.

| Propriété | | Source DataHub | Module |
|---|---|---|---|
| `a dcat:Dataset, dcat:Resource` | ⚙️ | constante | dataset.py |
| `dct:identifier` (`xsd:anyURI`) | M | `{base_uri}/dataset/{dataProductKey.id}` (URI de base de l'adoptant, obligatoire : `--base-uri` ou `base_uri` du profil) | dataproduct.py |
| `dct:title` | M | `dataProductProperties.name` | dataproduct.py |
| `dct:description` | M | `dataProductProperties.description` | dataproduct.py |
| `dct:alternative` | | `healthdcatap.acronym` | |
| `dcat:keyword` | M | `globalTags` (hors `dcat:sample`) | |
| `dcat:theme` | M | constante `.../data-theme/HEAL` (voir note) | |
| `dct:type` | M, =1 | `healthdcatap.datasetType` → `DatasetType` | |
| `dct:accessRights` | M, =1 | `healthdcatap.accessRights` → `AccessRights` | |
| `dcatap:applicableLegislation` | M | `healthdcatap.applicableLegislation` → `ApplicableRegulations` | |
| `dct:publisher` | M, =1 | `healthdcatap.publisher{Name,Homepage,Email,Type,Note}`, `.trustedDataHolder` | agents.py |
| `dct:creator` | | `healthdcatap.creator{Name,Homepage,Email}` | agents.py |
| `dcat:contactPoint` | M | `healthdcatap.contactPoint{Name,Email,Url}` | agents.py |
| `healthdcatap:hdab` | M, =1 | `healthdcatap.hdab{Name,Homepage,Email}` | agents.py |
| `dct:provenance` | M | `healthdcatap.provenance` | |
| `dpv:hasPurpose` | M | `healthdcatap.purpose` | |
| `healthdcatap:healthCategory` | M | `healthdcatap.healthCategory` → `HealthCategories` | |
| `healthdcatap:healthTheme` | M | `healthdcatap.healthTheme` → `HealthTheme` | |
| `dct:spatial` | M | `healthdcatap.spatialCoverage` → `PublicationsEuropAuthorityCountry` ou passage direct | |
| `dcat:distribution` | M, ≥1 | assets non tagués `dcat:sample` ; seulement les output ports si le DataProduct en déclare (ADR-0006) | dataset.py (reader) |
| `adms:sample` | M, ≥1 | assets tagués `dcat:sample` | dataset.py (reader) |
| `dct:language` | | `healthdcatap.language` → `PublicationsEuropAuthorityLanguage` | |
| `dct:issued` (`xsd:date`) | | `healthdcatap.issued` (un `date` — émis en `xsd:date`, pas `xsd:dateTime`) | |
| `dct:modified` (`xsd:dateTime`) | | ⚙️ le plus récent des `dct:modified` des distributions (`datasetProperties.lastModified` des assets, hors `adms:sample`) ; absent si aucun asset n'en porte. `dataProductProperties` n'a pas d'horodatage propre | dataproduct.py |
| `dct:temporal` | | `temporalCoverageStart`/`End` | |
| `dct:accrualPeriodicity` | | `publishingFrequency` → `Frequency` | |
| `dct:conformsTo` | | `referenceSpecification` → `ReferenceSpecification` (vocab d'auteur) ; code hors vocab → `{base_uri}/conformsTo/<code>` (ex. `OSIRIS`) | |
| `dct:license` | | `license`, passage direct | |
| `dct:isReferencedBy` | | `healthdcatap.isReferencedBy` ; DOI nu (`10.x/…`) ou `doi:` préfixé → `https://doi.org/…` | |
| `healthdcatap:numberOfRecords`/`numberOfUniqueIndividuals`/`min|maxTypicalAge` | | `number` | |
| `healthdcatap:populationCoverage` | | `healthdcatap.populationCoverage` | |
| `healthdcatap:retentionPeriod` | | `retentionPeriodStart`/`End` → `dct:PeriodOfTime` | |
| `healthdcatap:hasCodingSystem` | | `coding` → `CodingSystem` (vocabulaire d'auteur) | |
| `dpv:hasLegalBasis` | | `legalBasis` → `LegalBasis` (vocabulaire d'auteur) | |
| `dpv:hasPersonalData` | | `healthdcatap.personalData` → `PersonalData` | |
| `healthdcatap:hasStructuredData` (`xsd:boolean`, R7 1..1) | | dérivé : `true` ssi ≥1 asset porte un `schemaMetadata` (→ `csvw:Table`) | `model.py::HealthDataset.has_structured_data` ; toujours émis, `false` compris ; validateur HDH indifférent |
| `healthdcatap:hasVariables` → `csvw:TableGroup` (R7, `minCount 1` si `hasStructuredData`) | | ⚙️ regroupe par `csvw:table` toutes les `csvw:Table` du dataset (distributions + samples) | `dataset.py` ; émis ssi ≥1 `csvw:Table` ; nœud `<tablegroup:{uuid}>` ; validateur HDH indifférent (pas de `:CSVWTableGroup_Shape`) |
| `dcat:landingPage` | | `dataProductProperties.externalUrl` ; valeur qui n'est pas une IRI absolue → WARNING, ignorée | dataproduct.py |
| `foaf:page` | | `institutionalMemory.elements[].url`, un par lien, sans doublon ; valeur qui n'est pas une IRI absolue → WARNING, ignorée | dataproduct.py |
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
déjà `dcat:theme minCount 1`. Aucune propriété `healthdcatap.theme`
n'est nécessaire tant qu'aucun besoin de thème secondaire n'est identifié.

## Correspondance Dataset DataHub → `dcat:Distribution` / `adms:sample`

`:healthDistribution_Shape` (étend `:Distribution_Shape`) n'impose ses
exigences renforcées **qu'aux `dcat:distribution`** — un `adms:sample` reste
valide avec la seule `dcat:accessURL`.

| Propriété | Distribution | Sample | Source |
|---|---|---|---|
| `dcat:accessURL` | M | M | `healthdcatap.accessUrl` (`entityTypes:[dataset]`), repli `datasetProperties.externalUrl` |
| `dcat:byteSize` (`xsd:nonNegativeInteger`) | M, =1 | — | `datasetProfile.sizeInBytes` (aspect **timeseries**, lu via `ReadContext.get_dataset_profile` → `graph.get_latest_timeseries_value`) |
| `dct:format` | M, =1 | — | `healthdcatap.distributionFormat`, sinon déduit de l'extension du **nom technique** du dataset (jamais du displayName, qui ne la porte pas) |
| `dct:rights` (nœud `dct:RightsStatement`, pas un littéral direct — exigé `sh:BlankNodeOrIRI`) | M, =1 | — | hérité de `healthdcatap.license` du DataProduct |
| `dcatap:applicableLegislation` | M | — | hérité du DataProduct si l'asset n'en a pas |
| `dct:title` / `dct:description` | | | `datasetProperties.name`/`.description`, fusion `editableDatasetProperties` |
| `adms:status` | | | `healthdcatap.distributionStatus` → `DistributionStatus` ; `deprecation.deprecated` écrase en `WITHDRAWN` |
| `csvw:Table` → `csvw:column` | | | `schemaMetadata.fields` |

## Vocabulaires (`mapping/vocab/`)

12 fichiers vendus tels quels depuis
`hdh/.../controlled_vocabulary/controled_voc_dicts/` (voir `vocab/README.md`
pour la liste et la procédure de resynchronisation), plus quatre fichiers
d'auteur :

- **`LegalBasis.yml`** — mapping des 12 codes `eu-gdpr:A6-1-*`/`eu-gdpr:A9-2-*`
  vers l'extension GDPR du DPV (`https://w3id.org/dpv/legal/eu/gdpr#`).
- **`CodingSystem.yml`** — les 9 codes de `healthdcatap.coding`
  (SNOMED-CT, LOINC, ICD-10/11, ATC : URIs canoniques stables ; CIP13, UCD,
  CCAM, NABM : `CodeSystem.url` du Serveur Multi-Terminologies de l'ANS,
  `https://smt.esante.gouv.fr/terminologie-*`, CIP13 et UCD partageant celle du
  référentiel CIP/UCD ; vérifiées le 2026-10-29, cf.
  `docs/research/coding-system-uris.md`).
- **`ReferenceSpecification.yml`** — `HL7-FHIR-R4` → `http://hl7.org/fhir/4.0.1`,
  `OMOP-CDM-5.4` → page GitHub Pages OHDSI versionnée, `HL7v2` → `urn:hl7-org:v2xml`
  (URIs vérifiées le 2026-08-28, cf. `docs/research/reference-specification-uris.md`).
  Câblé dans `reader/dataproduct.py` ; code hors vocab → `{base_uri}/conformsTo/<code>`.
- **`DistributionStatus.yml`** — `COMPLETED` / `WITHDRAWN` → NAL EU Publications
  Office `.../distribution-status/*`. Câblé dans `reader/dataset.py` (`adms:status`) ;
  une dépréciation DataHub écrase en `WITHDRAWN`.

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
| `healthdcatap.publishingFrequency` allowedValue `IRREGULAR` | Le vocabulaire HDH `Frequency` attend `IRREG` — écart détecté par `resolve_or_warn` (dégradé en avertissement, pas d'échec) | à corriger dans `assets.yml` |
| `HealthCategories`/`HealthTheme` (URIs) | Repointées de l'hôte de dév en dur (`13.81.34.152:1101`) vers le namespace SEMIC `http://healthdataportal.eu/resource/authority/...` (issue #6). Aucun hôte canonique publié à ce jour → IRI pas encore déréférençables — voir `docs/research/hdh-healthdcat-ap-gaps.md` | resynchroniser quand l'EC/HDH publiera le vocabulaire officiel |
| `healthdcatap.retentionPeriod` (ancienne, texte ISO 8601) | Dépréciée au profit de `retentionPeriodStart`/`retentionPeriodEnd`, toujours déclarée dans `assets.yml` mais plus exportée | à retirer une fois la curation terminée |
| `PersonalData.yml` : mélange `dpv-pd#`/`pd#` + entrée `Death` sans terme DPV correspondant | Écarts confirmés présents à l'identique dans la source HDH (fichier vendu) le 2026-09-18, non corrigés localement (« HDH fait foi » — décision confirmée après un aller-retour sur `Death`, voir #86) — détail dans `docs/research/hdh-healthdcat-ap-gaps.md` | à signaler côté HDH pour resynchronisation |
