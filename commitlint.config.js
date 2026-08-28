// Politique de commits — ADR-0002.
// Vérifié en CI (wagoid/commitlint-github-action) sur les commits non-merge
// de la PR : git rev-list --no-merges BASE..HEAD.
module.exports = {
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
  },
};
