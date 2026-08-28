// Politique de commits — ADR-0002.
// Vérifié en CI (wagoid/commitlint-github-action) sur les commits non-merge
// de la PR : git rev-list --no-merges BASE..HEAD.
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', ['feat', 'fix', 'test', 'docs', 'chore', 'build']],
    'type-empty': [2, 'never'],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    // Pas de contrainte de casse sur le sujet (ADR-0002).
    'subject-case': [0],
    'header-max-length': [2, 'always', 72],
    // Scopes libres : aucune liste imposée.
    'scope-enum': [0],
    // Corps auto-générés (Dependabot : tableaux markdown + URLs de comparaison)
    // dépassent 100 caractères par ligne. La longueur de ligne du corps / pied
    // n'est pas une contrainte de l'ADR-0002, et #24 interdit un `if:` excluant
    // dependabot/* des checks — la config doit donc les tolérer.
    'body-max-line-length': [0],
    'footer-max-line-length': [0],
  },
};
