<!--
Le titre de la PR devient le sujet du commit de merge : il doit lui-même être
un Conventional Commit valide (feat / fix / test / docs / chore / build).
-->

## Résumé

<!-- Quoi et pourquoi, en quelques lignes. -->

## Checklist

- [ ] Chaque commit est signé DCO (`git commit -s`) et est un Conventional Commit valide (`feat` / `fix` / `test` / `docs` / `chore` / `build`), sujet ≤ 72, sans point final.
- [ ] Historique de branche propre (rebase interactif avant ouverture) — tous les commits atterrissent sur `main` via le commit de merge.
- [ ] `uv run pytest` passe.
- [ ] Si une correspondance de champ DataHub → HealthDCAT-AP a changé : `docs/mapping.md` est à jour.
- [ ] Si un vocabulaire contrôlé (`mapping/vocab/*.yml`) a changé : la valeur exacte attendue par les shapes SHACL du HDH a été vérifiée.
