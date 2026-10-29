# Data Product DataHub 1.8 : support et nouveaux alignements HealthDCAT-AP

Recherche rattachée à [#124](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/124)
(support des serveurs DataHub 1.7.x → 1.9.x, ADR-0004). Deux questions :

1. L'exporteur supporte-t-il le modèle Data Product du serveur 1.8 ?
2. Quels alignements HealthDCAT-AP nouveaux le modèle permet-il, sans casser 1.7 ?

Vérifié le 2026-10-29 contre les sources primaires listées en fin de document.

## État des versions

- Serveur OSS **v1.8.0** publié le 2026-10-22 (branche `releases/v1.8.0`) ; **v1.9.0rc1** le
  2026-10-27.
- Aucun client `acryl-datahub` 1.8.x n'est publié sur PyPI. Le `1.8.0rc4` présent est
  *yanked* (« wrong version number ») et son schéma est **plus ancien** que 1.7.0.18
  (`dataProductProperties` en `schemaVersion` 2 contre 3) : à ignorer.
- Les clients `1.7.0.x` suivent `master` : 1.7.0.18 contient déjà les champs du serveur 1.8
  décrits ci-dessous ; 1.7.0 ne les contient pas.

## Ce qui change dans le modèle Data Product

Comparaison des PDL `metadata-models/src/main/pegasus/com/linkedin/dataproduct/` et de
`entity-registry.yml` entre `releases/v1.7.0`, `releases/v1.8.0` et `releases/v1.9.0`.

| Changement | 1.7 | 1.8 | 1.9 | Nature |
|---|---|---|---|---|
| `dataProductProperties.parentDataProduct` (URN optionnel, relation `IsPartOf` vers `dataProduct`) | — | ✓ | ✓ | additif : hiérarchie parent-enfant, sur le modèle de `parentDomain` |
| Aspect `dataProducts` sur les assets (`array[DataProductAssociation]`) | — | ✓ | ✓ | miroir dénormalisé, **recherche seulement**, maintenu par `DataProductAssetsSideEffect` ; la source qui fait foi reste `dataProductProperties.assets` |
| `DataProductAssociation.outputPort` (booléen) | ✓ | ✓ | ✓ | inchangé, déjà présent en 1.7 |
| `dataProductProperties.externalUrl` | ✓ | ✓ | ✓ | inchangé |
| Type d'asset `api` dans `assets` | — | — | ✓ | 1.9 seulement |
| `DataProductKey`, liste des aspects de l'entité `dataProduct` | = | = | = | inchangés |

`dataProductProperties` ne porte **aucun** champ `lastModified`, ni en 1.7 ni en 1.8 :
`lastModified` existe seulement sur chaque `DataProductAssociation` (hérité de `Edge`).

Le CLI YAML (`datahub dataproduct upsert`) accepte `parent_data_product` et `output_ports`
dans les clients récents (1.7.0.18), mais toujours pas `structuredProperties`, d'où la
contrainte déjà documentée dans `reader/agents.py`.

## 1. Support : pas d'incompatibilité constatée

Sondes réalisées avec un payload au format 1.8 (`parentDataProduct` renseigné, asset avec
`outputPort`), désérialisé par `DataProductPropertiesClass.from_obj` :

| Client | `parentDataProduct` | Aspect asset `dataProducts` |
|---|---|---|
| 1.7.0 | ignoré sans erreur | inconnu : `get_entity_as_mcps` journalise `WARNING Ignoring unknown aspect type dataProducts` puis continue |
| 1.7.0.18 | lu | connu |

Conséquences :

- Le reader lit `dp.assets` (source qui fait foi) : inchangé en 1.8.
- La borne basse de la matrice CI (#127, `lowest-direct` = 1.7.0) contre un serveur 1.8
  produit **un avertissement par asset lu**. Ce n'est pas une panne, mais c'est du bruit. Le
  remède naturel : que `ReadContext.get_entity` demande explicitement les aspects que le
  reader exploite (paramètre `aspects` de `get_entity_semityped`). Ce n'est pas un
  aiguillage par version, donc c'est compatible avec ADR-0004 §4.
- Tout nouveau champ lu doit tolérer son absence (`getattr(…, None)`) : la borne basse du
  client ne le connaît pas, et un serveur 1.7 ne le renvoie pas.

### Défaut existant découvert : `dct:modified` jamais émis

`reader/dataproduct.py` lit `dp.lastModified`, qui n'existe pas sur `DataProductProperties`.
`getattr` renvoie toujours `None`, donc `dct:modified` n'est jamais émis contre un vrai
DataHub. Les tests passent parce que `tests/fixtures/fake_datahub.py` ajoute ce champ au
faux aspect. Indépendant de la version.

## 2. Nouveaux alignements possibles

Termes vérifiés dans `shapes/ehds/hdap-validator-sensitivity-shape.ttl`.

| Source DataHub | Dispo | Cible HealthDCAT-AP | Contrainte SHACL | Remarque |
|---|---|---|---|---|
| `parentDataProduct` | 1.8+ | `dcat:qualifiedRelation` → `dcat:Relationship` (`dct:relation` + `dcat:hadRole`), ou `dct:relation` | `:Dataset_Shape`, `BlankNodeOrIRI` ; `:Relationship_Shape` exige `dct:relation` et `dcat:hadRole` | `dct:isPartOf` n'est pas dans la shape `Dataset`. La cible doit être l'IRI stable `{base_uri}/dataset/{id}` (= `dct:identifier` du parent), pas `dataset:{id}` que le HDH régénère. `dcat:inSeries` est écarté : une série regroupe des éditions d'un même jeu de données, pas une taxonomie. |
| `outputPort` | 1.7+ | choix `dcat:distribution` / non exporté | — | Proposition : si le Data Product déclare au moins un output port, seuls les ports deviennent des distributions ; sinon comportement actuel. Change la sortie des adoptants qui déclarent des ports. |
| `dataProductProperties.externalUrl` | 1.7+ | `dcat:landingPage` | `:Dataset_Shape`, `BlankNodeOrIRI` | non lu aujourd'hui |
| `institutionalMemory.elements[].url` | 1.7+ | `foaf:page` | `:Dataset_Shape`, `BlankNodeOrIRI` | déjà listé « non lu en v1 » dans `docs/mapping.md` |
| Aspect asset `dataProducts` | 1.8+ | contrôle, pas de triple | — | Repère un asset membre de plusieurs Data Products (autorisé depuis datahub#16387). |

### Asset partagé entre plusieurs Data Products

Le nœud d'une distribution est `node_uri("distribution", <URN de l'asset>)`
(`mapping/distribution.py`) : il ne dépend que de l'asset. Si deux Data Products exportés
dans le même graphe partagent un asset, leurs triples fusionnent sur un seul nœud ; avec
deux `dct:rights` hérités différents, la contrainte `maxCount 1` de
`:healthDistribution_Shape` est violée. Le défaut existe dès 1.7 et se repère sans
l'aspect 1.8 (en comparant les assets de la sélection). L'aspect `dataProducts` permet
seulement de le signaler même quand l'autre Data Product n'est pas sélectionné.

### Hors périmètre 1.8

- Assets de type `api` (1.9) → candidat `dcat:DataService` / `dcat:accessService`. À
  instruire avec l'élargissement 1.9.

## Questions ouvertes

1. Relation au parent : `dcat:qualifiedRelation` (rôle explicite, quel vocabulaire de
   rôles ?) ou `dct:relation` simple ? Que faire quand le parent n'est pas dans la
   sélection ? L'ingestion HDH conserve-t-elle ces propriétés ? (non vérifié)
2. `outputPort` : le filtrage des distributions mérite-t-il un ADR et un changement
   cassant ?

## Tickets

Sous-issues de #124 ouvertes à partir de cette recherche :

| Ticket | Sujet | État |
|---|---|---|
| #141 | Élargir la plage à 1.8 | bloqué par #127, #129, #131 et la publication d'un client 1.8 |
| #142 | `ReadContext` demande explicitement les aspects lus | prêt |
| #143 | `dct:modified` jamais émis | source à choisir |
| #144 | Asset partagé entre DataProducts | prêt |
| #145 | `dcat:landingPage` + `foaf:page` | prêt |
| #146 | Hiérarchie `parentDataProduct` | à trancher (question 1) |
| #147 | Output ports → `dcat:distribution` | à trancher (question 2) |

## Sources

- datahub-project/datahub, branches `releases/v1.7.0`, `releases/v1.8.0`,
  `releases/v1.9.0` : `metadata-models/src/main/pegasus/com/linkedin/dataproduct/*.pdl`,
  `metadata-models/src/main/resources/entity-registry.yml`.
- `docs/how/updating-datahub.md` (branche `releases/v1.9.0`) : entrées « Metadata Model /
  Data Products » (`parentDataProduct`) et « GMS / search » (aspect asset `dataProducts`,
  `ResyncDataProductAssetsStep`).
- Wheels PyPI `acryl-datahub` 1.7.0, 1.7.0.18, 1.8.0rc4 (yanked) :
  `datahub/metadata/schemas/DataProduct*.avsc`, `datahub/ingestion/graph/client.py`
  (`get_entity_as_mcps`), `datahub/api/entities/dataproduct/dataproduct.py`.
