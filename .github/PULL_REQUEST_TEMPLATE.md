<!--
Merge par rebase : chaque commit de la branche atterrit tel quel sur `main` et
nourrit le changelog. Le titre de PR n'entre pas dans l'historique.
-->

## Résumé

<!-- Quoi et pourquoi, en quelques lignes. -->

## Checklist

- [ ] Chaque commit est signé DCO (`git commit -s`) et est un Conventional Commit valide (`feat` / `fix` / `test` / `docs` / `chore` / `build`), sujet ≤ 72, sans point final.
- [ ] Historique de branche propre, sans commit de merge (rebase interactif avant ouverture, mise à jour par rebase) — tous les commits atterrissent tels quels sur `main`.
- [ ] `uv run pytest` passe.
- [ ] Si une correspondance de champ DataHub → HealthDCAT-AP a changé : `docs/mapping.md` est à jour.
- [ ] Si un vocabulaire contrôlé (`mapping/vocab/*.yml`) a changé : la valeur exacte attendue par les shapes SHACL du HDH a été vérifiée.
