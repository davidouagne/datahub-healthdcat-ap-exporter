# Contrat des structured properties : préfixe `healthdcatap.*`, propriété du projet

Status: accepted

Contexte : session de grilling du 2026-10-28 sur
[#125](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/125). Le projet
vise d'autres **adoptants** que l'AP-HP — d'abord les entrepôts de santé français poussant
vers le Catalogue HDH. Or le contrat de lecture (les SP `fr.aphp.healthdcat.*`) imposait à
tout adoptant de créer des propriétés au nom de l'AP-HP, et leurs définitions vivaient dans
le registre interne AP-HP.

## Décisions

1. **Préfixe `healthdcatap.*`.** Les SP lues par l'exporteur sont renommées de
   `fr.aphp.healthdcat.<nom>` en `healthdcatap.<nom>` ; les noms locaux ne changent pas.
   Ce préfixe reprend celui du vocabulaire RDF `healthdcatap:` par lisibilité ; il ne
   revendique **aucune** autorité de la Commission européenne ni du projet HealthDCAT-AP :
   c'est le contrat de *cet exporteur*.

2. **Coupure nette.** L'ancien préfixe n'est plus lu, sans période de double lecture.
   Si l'instance ne définit aucune SP `healthdcatap.*` mais en définit en
   `fr.aphp.healthdcat.*`, l'exporteur s'arrête au démarrage avec une erreur unique
   renvoyant au guide de migration — diagnostic, jamais repli.

3. **Ce dépôt est la source de vérité des définitions.** Les définitions canoniques
   (type, cardinalité, valeurs autorisées, types d'entités) sont embarquées dans le paquet,
   versionnées avec l'exporteur, et écrites sur disque par `dh-healthdcat properties`.
   L'adoptant les applique avec `datahub properties upsert` : l'exporteur reste en lecture
   seule sur DataHub. Le registre AP-HP devient consommateur ; la migration de ses données
   (renommage des clés, réingestion, suppression des anciennes SP) lui appartient.

4. **Changements cassants livrés ensemble.** Ce renommage, l'**URI de base** obligatoire
   (plus de défaut `https://eds.aphp.fr`), le repli de `dct:conformsTo` dérivé de l'URI de
   base (`<base>/conformsTo/<code>` au lieu de `urn:aphp:conformsTo:<code>`) et le
   relèvement du plancher `acryl-datahub` (ADR-0004) partent dans une seule version
   cassante, avec un seul guide de migration.

## Options écartées

- **Garder `fr.aphp.healthdcat.*` comme convention de fait** : tout adoptant écrirait au
  nom de l'AP-HP.
- **Préfixe configurable** : aurait évité la migration AP-HP, mais laissé le contrat sans
  propriétaire ni définitions publiées ; chaque adoptant aurait réinventé les siennes.
- **`healthdcat.*`** : plus neutre, mais moins lisible face au vocabulaire RDF ;
  **domaine inversé du projet** : sans collision, mais lourd et lié à un compte personnel.
- **Double lecture transitoire** : migration progressive possible, au prix d'une logique de
  repli et de priorité à maintenir puis retirer.

## Conséquences

- L'AP-HP doit avoir migré son registre et ré-ingéré **avant** de monter de version.
- Si une définition officielle de SP HealthDCAT-AP pour DataHub apparaissait sous ce même
  préfixe, il faudra réconcilier ou renommer.
