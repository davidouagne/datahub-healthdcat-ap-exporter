# Hiérarchie de Data Products et output ports : règles de mapping

Status: accepted

Contexte : session de grilling du 2026-10-29 sur
[#146](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/146) et
[#147](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/147), à partir de
la recherche `docs/research/datahub-1.8-dataproduct.md`. Deux éléments du modèle DataHub ne
sont pas encore exploités :

- `dataProductProperties.parentDataProduct` (serveur 1.8+) : hiérarchie parent-enfant entre
  Data Products ;
- `DataProductAssociation.outputPort` (déjà en 1.7) : distingue, parmi les assets d'un Data
  Product, ceux qu'il expose de ceux qu'il utilise en interne.

Aujourd'hui, **tous** les assets deviennent des `dcat:distribution`. Les Data Products AP-HP
mélangent pourtant tables brutes, staging, modèles dbt et jobs avec la seule table
consommable — tout part dans le catalogue.

Le Catalogue HDH ne conserve pas le Turtle reçu : il le relit dans son modèle puis le
réécrit. `dct:relation`, `dct:isPartOf` et `dcat:inSeries` y sont perdus ;
`dcat:qualifiedRelation` est conservé, mais sa cible est réémise comme `dcat:DataService`
(voir `docs/research/hdh-healthdcat-ap-gaps.md`).

## Décisions

### Hiérarchie (`parentDataProduct`, #146)

1. **Un parent est un Data Product ordinaire.** Sélectionné, il devient un `dcat:Dataset`
   comme les autres ; aucun traitement particulier, même sans asset.

2. **Lien de l'enfant vers son parent direct, seulement.** Pas de lien inverse
   parent → enfants (il faudrait rechercher les enfants de chaque parent), pas de chaîne
   d'ancêtres (elle se reconstitue de proche en proche).

3. **Forme RDF : relation qualifiée, rôle IANA `up`.**

   ```turtle
   <enfant> dcat:qualifiedRelation [
       a dcat:Relationship ;
       dct:relation <{base_uri}/dataset/{id du parent}> ;
       dcat:hadRole <http://www.iana.org/assignments/relation/up>
   ] .
   ```

   C'est la seule forme à la fois admise par la shape HealthDCAT-AP (`:Dataset_Shape`,
   `:Relationship_Shape`) et conservée par le HDH, dont le vocabulaire `RoleQualifiedRelation`
   contient `up` (« document parent dans une hiérarchie »). La réémission de la cible en
   `dcat:DataService` par le HDH est un écart consigné, pas contourné.

4. **Cible : l'IRI stable du parent, toujours.** `{base_uri}/dataset/{id}` (= le
   `dct:identifier` du parent), jamais le nœud `dataset:{id}` que le HDH régénère. Le lien
   est émis même si le parent n'est pas dans la sélection : il peut être exporté ou poussé
   dans un autre passage, et la sortie d'un Data Product ne dépend pas des filtres choisis.

5. **Après l'élargissement à 1.8 (#141).** Un serveur 1.7 n'a jamais de parent, et
   ADR-0004 exclut toute lecture préventive d'une version hors plage vérifiée : #146 est
   bloqué par #141, lui-même en attente d'un client `acryl-datahub` 1.8 publié.

### Output ports (#147)

6. **Les ports choisissent les distributions.** Si un Data Product déclare au moins un
   output port, seuls ses assets ports deviennent des `dcat:distribution`. S'il n'en déclare
   aucun, comportement inchangé : tous ses assets.

7. **Un asset hors port n'existe pas pour l'export.** Dès qu'un port est déclaré, les autres
   assets ne produisent ni distribution, ni variables (`healthdcatap:hasVariables`), ne
   comptent pas dans `dct:modified` (maximum des distributions) et ne déclenchent pas
   l'avertissement d'asset partagé (#144).

8. **`dcat:sample` reste indépendant des ports.** Un asset tagué `dcat:sample` devient un
   `adms:sample`, port ou non : le tag est un choix éditorial explicite, les ports ne
   gouvernent que les `dcat:distribution`.

9. **Livraison sans rupture.** La règle de repli (6) garantit qu'aucune sortie ne change
   tant qu'aucun port n'est déclaré : #147 part en `feat`, dès maintenant (`outputPort`
   existe en 1.7).

## Options écartées

- **`dct:isPartOf`** : sens exact, mais absent de la shape `Dataset` et perdu par le HDH.
- **`dct:relation` direct** : admis par la shape, mais perdu par le HDH et sans rôle.
- **`dcat:inSeries`** : une série regroupe des éditions d'un même jeu de données, pas une
  taxonomie ; perdu par le HDH.
- **Rôle IANA `collection`** : désigne la ressource collection d'un élément ; `up` dit
  exactement « parent dans une hiérarchie ».
- **Lien seulement si le parent est dans la sélection** : la sortie d'un même Data Product
  changerait selon les filtres.
- **Ports exclusifs sans repli** : changerait la sortie de tous les adoptants qui ne
  déclarent pas de ports, c'est-à-dire tous aujourd'hui.
- **Reporter #146** faute d'adoptant : écarté, le support de la hiérarchie est prévu à
  court terme.

## Conséquences

- Les adoptants qui alimentent DataHub par `datahub-yaml-source` ne peuvent déclarer ni
  ports ni parent tant que cet outil ne les modélise pas (`DataProductDoc` : id, name,
  description, assets). L'évolution est suivie sur #146 et #147, pas sur le dépôt frère.
- Dans le catalogue HDH, le lien vers le parent apparaît comme une relation vers un
  « service » dont l'URL est celle du parent.
- La validation SHACL locale (shape sensibilité) continue de s'appliquer : un Data Product
  dont tous les ports sont des échantillons n'a aucune `dcat:distribution`, signalé comme
  aujourd'hui.
