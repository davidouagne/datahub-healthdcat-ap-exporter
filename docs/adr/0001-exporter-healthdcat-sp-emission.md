# Politique d'émission des structured properties HealthDCAT-AP côté exporteur

Status: accepted

Source amont des arbitrages : ADR-0005 (`docs/adr/0005-healthdcat-sp-coverage-audit.md`)
du dépôt `datahub-data-gov-registry`. Le présent ADR ne couvre que les suites
d'implémentation côté `datahub-healthdcat-ap-exporter`.

## 1. Dérivation de `healthdcatap:hasStructuredData` et `healthdcatap:hasVariables`

`hasStructuredData` (booléen, `1..1` en R7) est **dérivé**, pas saisi : `true` ssi au
moins un asset du DataProduct porte un `schemaMetadata` DataHub (⇒ une `csvw:Table`
construite par le reader). Il est **toujours émis**, `false` compris.
`hasVariables` est émis ssi `hasStructuredData` est vrai : un `csvw:TableGroup` au niveau
`dcat:Dataset` regroupe par `csvw:table` toutes les `csvw:Table` (distributions et
échantillons confondus).

Alternative écartée : porter ces deux propriétés par des structured properties saisies à
la main — rejetée car l'information existe déjà dans `schemaMetadata` et serait redondante
ou divergente.

Conséquences (écarts R7 résiduels, voir _Reporté_) :

- le proxy « `schemaMetadata` présent avec ≥ 1 champ » est plus étroit que la notion R7
  « contient des données structurées » — un CSV sans schéma enregistré est émis `false` ;
- le sous-arbre `csvw:TableGroup → csvw:Table → csvw:Column` n'est vérifié par aucun
  validateur : le validateur du Catalogue HDH cible `csvw:Table` / `csvw:Column` en
  isolation (`targetClass`), pas via `hasVariables`, et R7 n'est pas dans le CI ;
- `:CSVWColumnShape` (R7) exige `dct:description` par colonne ; l'exporteur ne l'émet que
  si la colonne en porte une dans `schemaMetadata`.

## 2. Politique d'URI `dct:conformsTo` / `referenceSpecification`

Un vocabulaire d'auteur `mapping/vocab/ReferenceSpecification.yml` mappe les codes de
`fr.aphp.healthdcat.referenceSpecification` vers des URIs canoniques : `HL7-FHIR-R4` →
`http://hl7.org/fhir/4.0.1` (version épinglée, pas l'étiquette mouvante `R4`),
`OMOP-CDM-5.4` → la page GitHub Pages OHDSI versionnée, `HL7v2` → `urn:hl7-org:v2xml`
(namespace XML officiel HL7 v2). Tout code hors vocabulaire — `OSIRIS` et tout code futur
non mappé — retombe **silencieusement** sur `urn:aphp:conformsTo:<code>`, cohérent avec le
traitement de `spatialCoverage`.

Conséquence : « canonique » est en partie aspirationnel — `OMOP-CDM-5.4` pointe une page
HTML et `HL7v2` un URN non déréférençable, faute de mieux publié.

## 3. URIs des vocabulaires HealthDCAT-AP non encore publiés

`healthCategory`, `healthTheme` (et, dans le même esprit, `publisherType`) utilisent le
namespace SEMIC `http://healthdataportal.eu/resource/authority/...`. Aucun vocabulaire
officiel EC/HDH n'est publié pour ces termes à ce jour : ces IRI **ne sont pas
déréférençables**. On préfère un identifiant SEMIC à l'hôte de développement en dur
(`http://13.81.34.152:1101/...`) hérité des sources HDH. Le validateur HDH n'exige qu'une
IRI (`sh:nodeKind sh:BlankNodeOrIRI`, aucun `sh:in`) — aucun impact fonctionnel.
Resynchroniser ces fichiers à la publication du vocabulaire officiel.

## Reporté

- **`trustedDataHolder`** (§E.1) : la SP est conservée uniquement parce que le validateur
  HDH l'exige (`:HealthPublisherAgent_Shape`, `sh:minCount 1`) ; le terme a été retiré de
  HealthDCAT-AP côté EC (brouillon SEMIC). La retirer dès que le validateur HDH s'alignera
  sur R7.
- **Revalidation R8** (§E.3) : revalider l'ensemble de la table des obligations et des
  décisions ci-dessus à la sortie de HealthDCAT-AP Release 8 (~2026-09).
