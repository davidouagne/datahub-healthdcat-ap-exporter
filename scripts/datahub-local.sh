#!/usr/bin/env bash
# Serveur DataHub local vide, isolé par version, pour l'inspecter à la main.
#
#   scripts/datahub-local.sh <version> up|down [--purge] [--project <nom>]
#
#   <version>          version du serveur, ex. 1.7.0 ou 1.8.0
#   up                 démarre (ou redémarre, données comprises) cette version
#   down               arrête le serveur, données conservées
#   --purge            avec down : supprime aussi conteneurs, volumes et réseau
#   --project <nom>    projet compose (défaut : dhhc-local-<version>), p. ex.
#                      dhhc-verify-<version> laissé par verify-datahub-version.sh --keep
#
# Aucun seed, aucun export : voir verify-datahub-version.sh pour le contrôle.
# Une version à la fois, sur les ports par défaut (UI 9002, GMS 8080) : `up`
# refuse de démarrer si un autre serveur répond déjà sur 8080. Prérequis :
# Docker, ~8 Go de RAM pour Docker.
#
# Isolation des données : volumes propres au projet, voir
# scripts/lib/datahub-isolation.sh. Le compose est conservé sous
# ~/.datahub/dhhc-local/<projet>/ pour redémarrer sur les mêmes données.
set -euo pipefail

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
}

version=""
action=""
purge=false
project=""
while [ $# -gt 0 ]; do
  case "$1" in
    up | down) [ -z "$action" ] && action="$1" || usage ;;
    --purge) purge=true ;;
    --project) [ $# -ge 2 ] || usage; project="$2"; shift ;;
    -h | --help) usage ;;
    -*) echo "Option inconnue : $1" >&2; usage ;;
    *) [ -z "$version" ] && version="${1#v}" || usage ;;
  esac
  shift
done
[ -n "$version" ] && [ -n "$action" ] || usage
[ "$purge" = false ] || [ "$action" = down ] || usage

root="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib/datahub-isolation.sh
. "$root/scripts/lib/datahub-isolation.sh"

isolation_env "${project:-dhhc-local-${version//./-}}"
state="$HOME/.datahub/dhhc-local/$DATAHUB_COMPOSE_PROJECT_NAME"
compose="$state/docker-compose.yml"

if [ "$action" = down ]; then
  if [ "$purge" = true ]; then
    step "Suppression du serveur $version (projet $DATAHUB_COMPOSE_PROJECT_NAME), volumes compris"
    purge_isolated
    rm -rf "$state"
  else
    step "Arrêt du serveur $version (projet $DATAHUB_COMPOSE_PROJECT_NAME), données conservées"
    stop_isolated
  fi
  exit 0
fi

if project_running && gms_up; then
  echo "Le serveur $version (projet $DATAHUB_COMPOSE_PROJECT_NAME) tourne déjà."
  exit 0
fi
if gms_up; then
  die "un autre serveur DataHub répond déjà sur $DATAHUB_GMS_URL : l'arrêter avant (aucune écriture faite)."
fi

mkdir -p "$state"
if [ ! -s "$compose" ]; then
  fetch_isolated_compose "$version" "$compose"
fi
start_isolated "$version" "$compose"

cat <<EOF

DataHub $version prêt (projet $DATAHUB_COMPOSE_PROJECT_NAME).
  UI  : http://localhost:9002 (datahub / datahub)
  GMS : $DATAHUB_GMS_URL
  Arrêt : scripts/datahub-local.sh $version down [--purge]
EOF
