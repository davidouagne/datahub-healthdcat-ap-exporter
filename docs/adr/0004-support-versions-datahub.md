# Politique de support des versions DataHub

Status: accepted

Contexte : session de grilling du 2026-10-28, implémentation suivie par
[#124](https://github.com/davidouagne/datahub-healthdcat-ap-exporter/issues/124).
Le projet est open source et vise d'autres contextes que l'AP-HP : la plage de versions
supportées est une promesse faite à des utilisateurs dont on ignore les serveurs.

## Décisions

1. **La cible est le serveur.** Une *Version DataHub supportée* (voir `CONTEXT.md`) est
   une version du GMS. La version de `acryl-datahub` n'est pas un engagement.

2. **La plage ne contient que des versions vérifiées.** Le plafond est la dernière mineure
   vérifiée, pas une version à venir : `acryl-datahub>=1.7,<1.8` aujourd'hui, même si
   l'objectif est 1.9. `pyproject.toml` est la source unique de la plage (serveur = client) ;
   tout le reste (avertissement au démarrage, CI, README) en dérive. Une mineure entre dans
   la plage par une PR d'élargissement, revue humainement, qui exige le contrôle Docker.

3. **Contrôle Docker local, pas en CI.** Une mineure se vérifie avec
   `scripts/verify-datahub-version.sh <version>` : serveur en Docker, seed minimal propre au
   dépôt (outils natifs `acryl-datahub` seulement), export, sensitivity shape, puis
   comparaison par isomorphisme RDF à une référence commitée. En CI, seule une matrice de
   tests unitaires `lowest-direct` / `highest` (doubles de test) vérifie la surface cliente.
   Les patchs restent en auto-merge.

4. **`reader/graph.py` est la seule frontière avec DataHub.** Toute adaptation entre
   versions y vit, et seulement après une incompatibilité constatée : pas d'aiguillage
   préventif par version.

5. **Hors plage : avertir, pas bloquer.** Au démarrage, la version GMS (`/config`) est
   comparée à la plage ; hors plage, non reconnue ou DataHub Cloud → avertissement,
   `--strict-version` → échec.

## Options écartées

- **Plafond large (`<1.10` ou `<2`)** : annoncerait des versions jamais vérifiées.
- **Workflow d'intégration Docker en CI** (requis ou déclenché par chemin) : coût
  (~10 min de quickstart par version) et complexité jugés disproportionnés pour des
  montées mineures rares, déjà soumises à revue humaine.
- **Seed issu de `aphp/datahub-sample` ou du registre AP-HP** : dépendance externe (dépôt
  sans tag, connecteur `datahub-yaml-source` qui doit lui-même suivre DataHub) et ancrage
  AP-HP contraire à l'ambition open source.
- **Refuser de s'exécuter hors plage** : bloquerait des utilisateurs dont le serveur
  fonctionne.

## Conséquences

- Relever le plancher de `>=0.14.1` (déjà faux : `datahub.sdk` est requis) à `>=1.7` est un
  changement cassant.
- Un utilisateur dont l'environnement impose un `acryl-datahub` d'une mineure non encore
  vérifiée ne peut pas installer l'exporteur sans forcer la résolution ; un serveur plus
  récent avec le client de la plage ne fait, lui, qu'avertir. C'est le prix d'une plage
  honnête.
