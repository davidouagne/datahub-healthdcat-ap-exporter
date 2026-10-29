# shellcheck shell=bash
# Isolation des données d'un serveur DataHub local, partagée par
# verify-datahub-version.sh et datahub-local.sh. À sourcer, pas à exécuter.
#
# Le compose officiel du quickstart nomme ses volumes en dur (`datahub_mysqldata`,
# `datahub_osdata`, `datahub_broker`). Un autre nom de projet ne suffit donc PAS :
# un serveur d'une autre version démarrerait sur les données d'un quickstart
# existant. On télécharge ce compose, on renomme les volumes au nom du projet,
# on refuse de démarrer si un serveur répond déjà sur 8080, et on vérifie les
# volumes montés avant toute écriture.
#
# Attend `root` (racine du dépôt) ; `isolation_env` fixe le projet compose.
# shellcheck disable=SC2154

step() { printf '\n== %s\n' "$*"; }
die() { echo "ERREUR : $*" >&2; exit 1; }

dh() { uv run --project "$root" datahub "$@"; }

# isolation_env <projet> : projet compose propre (volumes et réseau isolés).
isolation_env() {
  export DATAHUB_COMPOSE_PROJECT_NAME="$1"
  # Toujours le serveur local, jamais ~/.datahubenv (qui peut viser un autre
  # serveur) ; le quickstart n'active pas l'authentification.
  export DATAHUB_GMS_URL="http://localhost:8080"
  export DATAHUB_GMS_TOKEN=""
  # Sortie redirigée sous Windows : sans UTF-8, le CLI datahub plante en
  # affichant « ✔ » (cp1252). Seulement les flux standard : PYTHONUTF8 changerait
  # aussi l'encodage des fichiers, et le CLI ne relirait plus son
  # ~/.datahub/quickstart/.local-secrets.env, écrit dans l'encodage local.
  export PYTHONIOENCODING=utf-8
}

gms_up() {
  curl -sf -o /dev/null --max-time 5 "$DATAHUB_GMS_URL/health"
}

# fetch_isolated_compose <version> <fichier> : compose du quickstart, volumes
# renommés au nom du projet.
fetch_isolated_compose() {
  local version="$1" compose="$2" git_ref
  step "Compose du quickstart $version, volumes renommés pour le projet $DATAHUB_COMPOSE_PROJECT_NAME"
  # Même compose que `datahub docker quickstart --version` téléchargerait : sa
  # table de versions peut viser une autre référence git que le tag (v1.7.0 →
  # v1.7.0.1), dont le compose du tag ne démarre pas.
  git_ref="$(uv run --project "$root" python -c "
from datahub.cli.quickstart_versioning import QuickstartVersionMappingConfig as Q
print(Q.fetch_quickstart_config().get_quickstart_execution_plan('v$version').composefile_git_ref)
" 2>/dev/null | tail -1)"
  [ -n "$git_ref" ] || die "plan quickstart introuvable pour v$version"
  curl -sfL -o "$compose" \
    "https://raw.githubusercontent.com/datahub-project/datahub/$git_ref/docker/quickstart/docker-compose.quickstart-profile.yml" \
    || die "compose introuvable pour $git_ref"
  echo "Compose de la référence $git_ref"
  sed -i "s/^    name: datahub_/    name: ${DATAHUB_COMPOSE_PROJECT_NAME}_/" "$compose"
  if grep -q "name: datahub_" "$compose"; then
    die "volume datahub_* restant dans le compose : isolation impossible"
  fi
}

project_filter() { echo "label=com.docker.compose.project=$DATAHUB_COMPOSE_PROJECT_NAME"; }

project_running() {
  [ -n "$(docker ps -q --filter "$(project_filter)")" ]
}

# stop_isolated : arrête les conteneurs du projet, données conservées.
stop_isolated() {
  docker ps -q --filter "$(project_filter)" | xargs -r docker stop >/dev/null
}

# purge_isolated : supprime conteneurs, volumes et réseau du projet, et eux
# seuls. Pas `datahub docker nuke` : il supprime aussi, quel que soit le projet,
# les volumes `datahub_mysqldata`, `datahub_broker`… d'un quickstart par défaut.
purge_isolated() {
  docker ps -aq --filter "$(project_filter)" | xargs -r docker rm -f -v >/dev/null
  docker volume ls -q --filter "$(project_filter)"     | { grep "^${DATAHUB_COMPOSE_PROJECT_NAME}_" || true; }     | xargs -r docker volume rm >/dev/null
  docker network ls -q --filter "$(project_filter)" | xargs -r docker network rm >/dev/null
}

# start_isolated <version> <fichier> : démarre le serveur, puis vérifie que
# MySQL monte bien le volume du projet (dernier garde-fou avant toute écriture).
start_isolated() {
  local version="$1" compose="$2" mounts
  step "Démarrage du serveur DataHub $version"
  dh docker quickstart --version "v$version" --no-accept-version-default -f "$compose"
  mounts="$(docker inspect "$DATAHUB_COMPOSE_PROJECT_NAME-mysql-1" --format '{{range .Mounts}}{{.Name}} {{end}}')"
  case "$mounts" in
    *"${DATAHUB_COMPOSE_PROJECT_NAME}_mysqldata"*) ;;
    *) die "MySQL monte « $mounts », pas le volume du projet : arrêt avant toute écriture." ;;
  esac
}
