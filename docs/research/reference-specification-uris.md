# URIs canoniques des standards de référence (`dct:conformsTo`)

Recherche préalable à la création de
`src/dh_healthdcat/mapping/vocab/ReferenceSpecification.yml`, qui doit mapper les
`allowedValues` de la structured property `fr.aphp.healthdcat.referenceSpecification`
(registre : `input/structured-property/hdcat-provenance/referencespecification.yml`)
vers de vraies IRI. Sans ce vocab, l'exporteur produit `URIRef("HL7-FHIR-R4")`,
c'est-à-dire une IRI relative invalide (cf.
`datahub-data-gov-registry/docs/research/healthdcat-ap-sp-file-audit.md`).

Périmètre : `HL7-FHIR-R4`, `OMOP-CDM-5.4`, `HL7v2`. `OSIRIS` **reste hors périmètre**
et conserve son enveloppe `urn:aphp:conformsTo:OSIRIS` (pas d'URI publique stable).

Vérifié le 2026-08-28 contre les sources primaires listées.

## Rappel du besoin

`referenceSpecification` → `dct:conformsTo` (le terme AP-HP `healthdcat:referenceSpecification`
n'existe pas dans HealthDCAT-AP ; `dct:conformsTo` est la propriété du profil, applicable
au `dcat:Dataset` **et** à la `dcat:Distribution`). La valeur attendue est une IRI
désignant un `dct:Standard`. Le SHACL du HDH n'impose qu'un `sh:nodeKind sh:BlankNodeOrIRI`
sans `sh:in` : n'importe quelle IRI passe la validation, mais on veut une IRI *signifiante
et stable*.

Le registre (`datahub-data-gov-registry`) ne modélise nulle part `dct:conformsTo` avec des
URI réelles : l'ADR 0005 et `docs/research/consolidation-todo.md` renvoient explicitement
la construction de ce vocab à l'exporteur (« A canonical-URI vocabulary for
`referenceSpecification`'s four values is a further exporter-side follow-up »). Aucun
précédent interne à recopier, donc ; ce document tient lieu de justification.

## HL7-FHIR-R4

**URI canonique retenue : `http://hl7.org/fhir/4.0.1`** (versionnée, schéma `http://`).

- HL7 identifie la release R4 par le numéro de version **`4.0.1`** (« publication.major.minor.revision »,
  4 = Release 4, correction technique n°1 du 2019-11-01). C'est l'identifiant que HL7
  utilise lui-même comme canonique de version pour le paquet cœur `hl7.fhir.r4.core#4.0.1`
  et comme code du CodeSystem `http://hl7.org/fhir/FHIR-version`.
  Source : <https://hl7.org/fhir/R4/versions.html>.
- Les canoniques HL7 FHIR sont déclarés avec le schéma **`http://`** par convention (même
  si le contenu est servi en `https://`). On aligne donc `ReferenceSpecification.yml` sur
  `http://` — cohérent avec `CodingSystem.yml` du même dépôt (`http://hl7.org/fhir/sid/icd-10`,
  `http://loinc.org`).
- **Forme : épingler la version.** `dct:conformsTo` doit désigner un standard précis.
  - `http://hl7.org/fhir/4.0.1` est non ambigu.
  - `http://hl7.org/fhir/R4` est une **étiquette de release** mouvante (R4 a d'abord été
    4.0.0, puis 4.0.1 après correction technique). À éviter comme *valeur* de conformité.
- **Forme résolvable :** `https://hl7.org/fhir/R4/` est le « permanent home » de la spec R4
  (« will always be available at this URL »). `http://hl7.org/fhir/R4` **et**
  `http://hl7.org/fhir/4.0.1` redirigent tous deux vers `hl7.org/fhir/R4/index.html`
  (vérifié). L'URI canonique retenue est donc *aussi* déréférençable en pratique — bonus,
  pas une exigence.
  Sources : <https://hl7.org/fhir/R4/index.html>, <http://hl7.org/fhir/R4>, <http://hl7.org/fhir/4.0.1>.
- Option : exposer en plus `https://hl7.org/fhir/R4/` via `foaf:page`/`rdfs:seeAlso` pour
  le lecteur humain, mais la valeur de `dct:conformsTo` = `http://hl7.org/fhir/4.0.1`.

## OMOP-CDM-5.4

**URI canonique retenue : `https://ohdsi.github.io/CommonDataModel/cdm54.html`**
(versionnée dans le chemin, schéma `https://` natif).

- **Il n'existe pas d'URI abstraite façon HL7** pour l'OMOP CDM. OHDSI ne publie pas de
  registre d'IRI ni de namespace canonique : la spécification est un site GitHub Pages.
- La page **v5.4** officielle est `https://ohdsi.github.io/CommonDataModel/cdm54.html`
  (« This is the specification document for the OMOP Common Data Model, v5.4 » — description
  haut niveau, conventions ETL, contraintes par table/champ). C'est l'artefact le plus
  autoritatif et le plus stable qu'OHDSI propose pour cette version.
  Sources : <https://ohdsi.github.io/CommonDataModel/cdm54.html>,
  <https://ohdsi.github.io/CommonDataModel/> (index des versions du CDM).
- **Forme : version épinglée, résolvable.** Le `5.4` est porté par le segment `cdm54`
  du chemin. `https://` d'origine.
- **Alternatives** (non retenues, à documenter) :
  - `https://github.com/OHDSI/CommonDataModel/tree/v5.4.0` — tag de release immuable
    (DDL 5.4 figées). À préférer *seulement* si on veut une immutabilité stricte au
    patch près. Source : <https://github.com/OHDSI/CommonDataModel/releases>.
  - `https://ohdsi.github.io/CommonDataModel/` — sans version, trop imprécis pour
    `dct:conformsTo`.
- **Ambiguïté mineure :** la ligne 5.4 a des points de version (`v5.4.0`, `v5.4.1`). Le code
  `OMOP-CDM-5.4` vise la *minor line* 5.4 ; `cdm54.html` suit cette ligne — cohérent avec
  l'intention du code. Pas de DOI Zenodo officiel pour le paquet `CommonDataModel` (recherché,
  rien trouvé).

## HL7v2

**Pas d'URI canonique unique — c'est un fait à assumer et à écrire tel quel.**
HL7 v2 est une **famille** de versions (2.1 … 2.9.1) ; le code `HL7v2` est
délibérément non versionné, et HL7 ne définit aucune IRI « le standard v2 » façon
`http://hl7.org/fhir/...`.

**Meilleure option disponible retenue : `urn:hl7-org:v2xml`.**

- C'est le **namespace XML officiel** des messages HL7 v2 (schémas v2.x XML : `urn:hl7-org:v2xml`
  y est à la fois *default* et *target namespace* ; les parseurs l'exigent). Identifiant réel,
  détenu par HL7, stable depuis ~20 ans. **Non déréférençable** (URN), comme les entrées
  placeholder assumées de `CodingSystem.yml` (`https://aphp.fr/codesystem/...`).
  Source : schémas HL7 v2.x Messaging Schemas — product brief
  <https://www.hl7.org/implement/standards/product_brief.cfm?product_id=213> ; usage
  documenté p. ex. HAPI HL7v2, BizTalk Accelerator for HL7.
- **Forme résolvable, humaine :** `https://www.hl7.org/implement/standards/product_brief.cfm?product_id=185`
  (« HL7 Version 2 Product Suite »). `https://`, mais URL à query-string — fragile, mauvais
  *identifiant*. À réserver à `foaf:page`, pas à la valeur de `dct:conformsTo`.
  Source : <https://www.hl7.org/implement/standards/product_brief.cfm?product_id=185>.
- **Choix pragmatique, pas un canonique normatif.** `urn:hl7-org:v2xml` porte à l'origine
  la sémantique « encodage XML des messages v2 », pas « conformité générique au standard v2 ».
  On l'accepte faute de mieux dans l'écosystème HL7.
- **Repli acceptable** si l'équipe refuse cette surcharge sémantique : garder
  `urn:aphp:conformsTo:HL7v2` (même traitement qu'`OSIRIS`). À trancher à l'implémentation
  du vocab ; recommandation de cette recherche = `urn:hl7-org:v2xml`.

## Tableau de recommandation

| Code | URI canonique | Forme | Source primaire |
|---|---|---|---|
| `HL7-FHIR-R4` | `http://hl7.org/fhir/4.0.1` | Versionnée (`4.0.1`, pas `R4`) ; schéma `http://` par convention HL7 ; résolvable de fait (redirige vers `hl7.org/fhir/R4/`) | HL7 FHIR, <https://hl7.org/fhir/R4/versions.html> + <http://hl7.org/fhir/4.0.1> |
| `OMOP-CDM-5.4` | `https://ohdsi.github.io/CommonDataModel/cdm54.html` | Version épinglée dans le chemin (`cdm54`) ; `https://` natif ; résolvable ; pas d'IRI abstraite existante | OHDSI, <https://ohdsi.github.io/CommonDataModel/cdm54.html> |
| `HL7v2` | `urn:hl7-org:v2xml` | **Pas de canonique unique** ; namespace XML HL7 v2, non versionné, non déréférençable ; page humaine `product_id=185` en `foaf:page` | Schémas HL7 v2.x XML ; <https://www.hl7.org/implement/standards/product_brief.cfm?product_id=213> et `?product_id=185` |
| `OSIRIS` | *(hors périmètre)* `urn:aphp:conformsTo:OSIRIS` | URN AP-HP local, pas d'URI publique stable | — |

## Impact sur `ReferenceSpecification.yml`

- Fichier **d'auteur** (pas vendu du HDH), à ranger comme `LegalBasis.yml` /
  `CodingSystem.yml` : en-tête de commentaire expliquant l'origine des URI et le statut
  de `HL7v2` (choix pragmatique) et d'`OSIRIS` (URN local conservé).
- `vocabulary_list` : les 3 codes → URI ci-dessus. Décider si `OSIRIS` est dans le vocab
  avec son `urn:aphp:*` ou laissé au fallback `_as_uri(..., "aphp:conformsTo")` de
  `reader/dataproduct.py` (qui enveloppe déjà tout code non-URI en `urn:aphp:conformsTo:<code>`).
- `reader/dataproduct.py` : `_as_uri` laisse passer une valeur qui est déjà une URI
  (`http://` / `https://` / `urn:`). Résoudre le code via le vocab **avant** `_as_uri`
  suffit ; aucune modif de `_as_uri` nécessaire.
- Revalider si : FHIR publie une nouvelle correction technique R4 (peu probable, R4 gelée) ;
  OHDSI réorganise le site CommonDataModel ; l'équipe tranche le repli `urn:aphp:*` pour `HL7v2`.
