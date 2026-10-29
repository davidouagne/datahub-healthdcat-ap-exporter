# URIs canoniques des systèmes de codage français (`healthdcatap:hasCodingSystem`)

Recherche pour l'issue #137 : remplacer les placeholders provisoires de
`src/dh_healthdcat/mapping/vocab/CodingSystem.yml`
(`https://aphp.fr/codesystem/{cip13,ucd,ccam,nfs}`) par l'identifiant officiel de
chaque nomenclature, émis comme valeur de `healthdcatap:hasCodingSystem` dans l'export
RDF HealthDCAT-AP.

Périmètre : `CIP13`, `UCD`, `CCAM`, `NFS`. Les autres entrées du vocab (`SNOMED-CT`,
`LOINC`, `ICD-10`, `ICD-11`, `ATC`) sont hors périmètre.

Vérifié le 2026-10-29 contre les sources primaires listées (pages SMT, serveur FHIR
du SMT interrogé en direct, paquet `ans.fr.terminologies#1.14.0`).

## Rappel du besoin

La valeur attendue est l'IRI qui identifie le *système de codage* (au sens
`Coding.system` FHIR / `skos:ConceptScheme`), pas une page web ni un concept. On veut
une IRI *détenue par l'organisme qui publie la terminologie* et stable.

Pour les terminologies de santé françaises, cet organisme est l'**ANS**, via le
**Serveur Multi-Terminologies (SMT)**, `smt.esante.gouv.fr`. Le SMT publie chaque
terminologie comme `CodeSystem` FHIR dont l'`url` est de la forme
`https://smt.esante.gouv.fr/terminologie-<nom>`. Cette forme est :

- l'`url` déclarée par la ressource `CodeSystem` sur le serveur FHIR du SMT
  (<https://smt.esante.gouv.fr/fhir/CodeSystem>) et dans l'IG ANS « Terminologies de
  Santé » (<https://interop.esante.gouv.fr/terminologies/>, v1.14.0) ;
- la valeur de `system` que l'ANS utilise elle-même dans ses jeux de valeurs CI-SIS
  (p. ex. `jdv-static-sem-procedure-cisis`, `jdv-type-acte-post-partum-cisis` incluent
  des codes CCAM sous `system = https://smt.esante.gouv.fr/terminologie-ccam`) ;
- résolvable de fait : `https://smt.esante.gouv.fr/terminologie-<nom>` redirige (301)
  vers la page humaine `…/terminologie-<nom>/` (vérifié pour les quatre terminologies
  citées ici). Bonus, pas une exigence.

Le SMT expose aussi, pour chaque terminologie, un **namespace de concepts OWL** sous
`http://data.esante.gouv.fr/…` (p. ex. `http://data.esante.gouv.fr/cnam/ccam/…`). Il
désigne les *concepts* et les propriétés, pas le système de codage, et l'ANS l'a
modifié plusieurs fois en 2026 (cf. flux RSS des pages SMT). **Non retenu** pour
`hasCodingSystem`.

FR Core (HL7 France, `hl7.fhir.fr.core#2.2.0`) ne définit aucun `CodeSystem` ni
`NamingSystem` pour CIP, UCD, CCAM ou NABM (vérifié sur
<https://hl7.fr/ig/fhir/core/artifacts.html>). terminology.hl7.org n'en enregistre pas
non plus. Le SMT est donc la seule source primaire.

## CCAM

**URI canonique retenue : `https://smt.esante.gouv.fr/terminologie-ccam`.**

- `CodeSystem` `terminologie-ccam` sur le serveur FHIR du SMT :
  `url = https://smt.esante.gouv.fr/terminologie-ccam`, version `v84.00`, publisher
  « Agence du numérique en santé », description « terminologie de facturation créée et
  maintenue par la CNAM », licence LOv2.
  Sources : <https://smt.esante.gouv.fr/fhir/CodeSystem/terminologie-ccam>,
  <https://interop.esante.gouv.fr/terminologies/CodeSystem-terminologie-ccam.html>.
- **OID : `1.2.250.1.215.300.1`** (`urn:oid:1.2.250.1.215.300.1`), déclaré en
  `identifier` (`use = usual`) et affiché comme « Identifiant(s) » sur la page SMT.
  Source : <https://smt.esante.gouv.fr/terminologie-ccam/>.
- **Changement d'OID à connaître.** L'historique FHIR du SMT montre que la version 2
  de la ressource (CCAM v76, 2024-10-30) portait `urn:oid:1.2.250.1.213.2.5` — l'OID
  historique des volets CDA du CI-SIS. Les versions actuelles portent
  `1.2.250.1.215.300.1`. L'`url` `https://`, elle, n'a pas changé depuis la version 1.
  C'est un argument de plus pour émettre l'URI `https://` plutôt que l'OID.
  Source : <https://smt.esante.gouv.fr/fhir/CodeSystem/terminologie-ccam/_history/2>.
- **Propriétaires :** la CNAM produit la CCAM (site de publication
  <https://www.ameli.fr/accueil-de-la-ccam/index.php>) ; ni la CNAM ni l'ATIH ne
  publient d'URI ou d'OID propre pour la nomenclature. L'ANS est le registraire.
- **Divergence observée, non retenue :** l'IG ANS « socle commun EDS » (brouillon
  `0.1.0`, <https://ansforge.github.io/IG-FHIR-EDS-SOCLE-COMMUN/CodeSystem-CCAM.html>)
  déclare son propre `CodeSystem` CCAM sous
  `https://interop.esante.gouv.fr/ig/fhir/eds/CodeSystem/CCAM`, sans OID. C'est un IG
  de travail, pas le registre ; le SMT fait foi.

## CIP13

**URI canonique retenue : `https://smt.esante.gouv.fr/terminologie-cip_ucd`** —
la même que pour `UCD` (voir ci-dessous).

- Le SMT ne publie **pas** de terminologie « CIP » seule. Les codes CIP13 sont portés
  par le **« Référentiel UCD »** du Club Inter-Pharmaceutique, terminologie unique qui
  « contient les codes des médicaments dispensés à l'hôpital (UCD), les codes des
  médicaments dispensés en milieu ambulatoire (CIP) » et formalise le lien entre eux.
  Identifiant SMT : `terminologie-cip_ucd`. Source :
  <https://smt.esante.gouv.fr/terminologie-cip_ucd/>.
- **`system` :** `https://smt.esante.gouv.fr/terminologie-cip_ucd`. Attesté par :
  - le jeu de valeurs ANS `vs-cipucd-all` (`compose.include.system`) ;
  - les `ConceptMap` ANS `alignement-bdpm-cipucd` et `alignement-nuva-cipucd`, dont le
    groupe cible est `https://smt.esante.gouv.fr/terminologie-cip_ucd` avec des codes
    CIP13 (p. ex. `3400933333577`).
  Sources : <https://interop.esante.gouv.fr/terminologies/ValueSet-vs-cipucd-all.html>,
  <https://smt.esante.gouv.fr/fhir/ConceptMap/alignement-bdpm-cipucd>.
- **Aucune ressource `CodeSystem` publique** pour cette `url` : la recherche
  `CodeSystem?url=…` sur le serveur FHIR du SMT renvoie 0 résultat, et `$lookup` /
  `$expand` échouent (« Could not find the code system …|2026-10 »). Cohérent avec la
  licence propriétaire (« Licence Club Inter Pharmaceutique », téléchargement soumis à
  acceptation). L'URI est donc attestée par son usage dans les ressources ANS, pas par
  une ressource `CodeSystem` consultable.
- **OID : `1.2.250.1.213.2.62`** (`urn:oid:1.2.250.1.213.2.62`), affiché comme
  « Identifiant(s) » sur la page SMT du Référentiel UCD. Source :
  <https://smt.esante.gouv.fr/terminologie-cip_ucd/>.
- **Alternative examinée — BDPM :** `https://smt.esante.gouv.fr/terminologie-bdpm`
  (base de données publique des médicaments, gérée par l'ANSM, LOv2). Ses codes de
  présentation **sont** des CIP13 (cf. `alignement-bdpm-cipucd`, qui aligne code pour
  code). Mais la BDPM ne couvre que les présentations commercialisées sur les cinq
  dernières années, et n'a pas d'OID (seul `identifier` : `terminologie-bdpm`). À
  retenir **seulement** si l'équipe veut un système sous licence ouverte et sait que
  les jeux décrits ne contiennent que des CIP de la BDPM.
  Source : <https://smt.esante.gouv.fr/fhir/CodeSystem/terminologie-bdpm>.
- Pistes sans résultat : FR Core, terminology.hl7.org, ANSM (aucune URI publiée pour
  le code CIP), un OID « CIP » isolé en `1.2.250.1.213.2.3.x` (introuvable dans les
  sources ANS consultées).

## UCD

**URI canonique retenue : `https://smt.esante.gouv.fr/terminologie-cip_ucd`**,
OID `1.2.250.1.213.2.62` — même terminologie que `CIP13` (Référentiel UCD du Club
Inter-Pharmaceutique), mêmes sources que ci-dessus.

- **Conséquence : `CIP13` et `UCD` pointent vers la même IRI.** Dans le vocabulaire,
  les deux clés se distinguent toujours par leur libellé, mais en RDF un consommateur ne
  pourra plus savoir si un jeu est codé en CIP13 ou en UCD. C'est un fait du registre
  ANS, pas une approximation de l'exporteur : la CIP et l'UCD sont gérées comme un seul
  référentiel (les deux familles de codes ont d'ailleurs 13 chiffres et le même préfixe
  `3400`).
- Pas d'alternative publique : l'UCD n'est pas dans la BDPM.

## NFS — ambiguïté

**Décision (2026-10-29, mainteneur) : lecture (a).** `NFS` est renommée `NABM` et
mappée vers `https://smt.esante.gouv.fr/terminologie-nabm` (#138, 0.3.0). L'analyse
ci-dessous est conservée telle qu'elle a été soumise.

La valeur `NFS` a été introduite comme valeur de démonstration
nue (sans description) dans le registre le 2026-05-31 ; aucun asset ne l'utilise ; le
libellé « Nomenclature française (biologie) » a été inventé côté exporteur. Aucune
terminologie nommée « NFS » n'existe au SMT (recherche dans les 358 `CodeSystem` et les
`NamingSystem` du serveur FHIR du SMT : rien).

Lectures plausibles et URI candidate pour chacune :

| Lecture | Système de codage ? | URI candidate | OID | Source |
|---|---|---|---|---|
| (a) **NABM** — Nomenclature des actes de biologie médicale (le libellé inventé « … (biologie) » y pointe) | Oui | `https://smt.esante.gouv.fr/terminologie-nabm` | `1.2.250.1.215.300.2` | <https://smt.esante.gouv.fr/fhir/CodeSystem/terminologie-nabm>, <https://smt.esante.gouv.fr/terminologie-nabm/> (v`V105`, LOv2) |
| (b) **Numération Formule Sanguine** — examen de biologie, pas une nomenclature | Non : c'est un *code* | aucune — le jeu serait plutôt codé dans un système qui *contient* la NFS : la NABM (acte `1104` « HEMOGRAMME Y COMPRIS PLAQUETTES (NFS , NFP) », vérifié par `$lookup` sur le SMT, NABM V105) ou LOINC (déjà dans le vocab) | — | <https://smt.esante.gouv.fr/terminologie-nabm/> |
| (c) Autre | — | aucune nomenclature française nommée « NFS » trouvée | — | — |

Notes :

- Pour la NABM, l'OID `1.2.250.1.215.300.2` est présent sans interruption depuis la
  version 8 de la ressource (NABM V96) ; les versions antérieures n'avaient pas d'OID
  ou déjà celui-ci (jamais un autre). L'`url` n'a pas changé depuis la version 1.
  Le namespace de concepts OWL a été changé en 2026 pour
  `http://data.esante.gouv.fr/dgos/nabm/` (flux RSS SMT) — non retenu, cf. Rappel.
- Les lectures (a) et (b) convergent en pratique : si `NFS` voulait dire « numération
  formule sanguine », le système de codage du jeu serait vraisemblablement la NABM ou
  LOINC, et la valeur `NFS` devrait disparaître du vocab plutôt que recevoir une URI.

**Question pour l'utilisateur :** que désigne `NFS` dans l'intention de l'auteur du
registre ?

1. La NABM → renommer la valeur en `NABM` côté registre et mapper vers
   `https://smt.esante.gouv.fr/terminologie-nabm` ?
2. La numération formule sanguine (confusion de saisie) → supprimer `NFS` des
   `allowedValues` et du vocab ?
3. Autre chose → laquelle ?

## Tableau de recommandation

| Code | URI canonique | OID (forme `urn:oid:`) | Forme | Source primaire |
|---|---|---|---|---|
| `CIP13` | `https://smt.esante.gouv.fr/terminologie-cip_ucd` | `urn:oid:1.2.250.1.213.2.62` | `system` du Référentiel UCD (CIP + UCD) ; `https://` ; pas de `CodeSystem` public (licence CIP) ; partagée avec `UCD` | ANS SMT, <https://smt.esante.gouv.fr/terminologie-cip_ucd/> + `vs-cipucd-all`, `alignement-bdpm-cipucd` |
| `UCD` | `https://smt.esante.gouv.fr/terminologie-cip_ucd` | `urn:oid:1.2.250.1.213.2.62` | Idem `CIP13` | Idem |
| `CCAM` | `https://smt.esante.gouv.fr/terminologie-ccam` | `urn:oid:1.2.250.1.215.300.1` (anciennement `1.2.250.1.213.2.5`) | `CodeSystem.url` SMT ; `https://` ; utilisée par les JDV CI-SIS | ANS SMT, <https://smt.esante.gouv.fr/fhir/CodeSystem/terminologie-ccam> |
| `NABM` (ex-`NFS`) | `https://smt.esante.gouv.fr/terminologie-nabm` | `urn:oid:1.2.250.1.215.300.2` | `CodeSystem.url` SMT ; `https://` ; voir section NFS | ANS SMT, <https://smt.esante.gouv.fr/fhir/CodeSystem/terminologie-nabm> |

**Forme canonique : l'URI `https://`, pas l'OID.** L'ANS déclare l'`https://` comme
`CodeSystem.url` (le canonique FHIR) et l'emploie comme `system` dans ses propres jeux
de valeurs ; l'OID n'est qu'un `identifier` secondaire, et il a déjà changé pour la
CCAM. On aligne donc sur `https://smt.esante.gouv.fr/terminologie-<nom>` — schéma
`https://` natif, à la différence des canoniques HL7 en `http://` déjà présents dans
`CodingSystem.yml`.

## Impact sur `CodingSystem.yml`

- Remplacer `CIP13`, `UCD`, `CCAM` par les URI ci-dessus ; renommer `NFS` en `NABM`
  avec l'URI NABM (changement cassant pour les valeurs saisies `NFS`).
- Mettre à jour le commentaire d'en-tête : ces trois-là ne sont plus des placeholders
  AP-HP mais les `CodeSystem.url` du SMT de l'ANS ; signaler que `CIP13` et `UCD`
  partagent volontairement la même IRI.
- Les libellés `fr` de `CIP13` / `UCD` restent distincts ; envisager pour `UCD`
  « Référentiel UCD (Club Inter-Pharmaceutique) » si l'on veut refléter le nom SMT.
- Revalider si : l'ANS publie un `CodeSystem` public pour `terminologie-cip_ucd` ou
  scinde CIP et UCD ; l'OID de la CCAM ou de la NABM change encore (sans effet sur
  l'URI retenue) ; FR Core ajoute des `NamingSystem` pour ces nomenclatures.
