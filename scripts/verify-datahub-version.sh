#!/usr/bin/env bash
# Contrôle Docker local d'une version du serveur DataHub (ADR-0004 §3).
#
#   scripts/verify-datahub-version.sh <version> [--update-reference] [--keep]
#
#   <version>            version du serveur, ex. 1.7.0
#   --update-reference   réécrit la référence au lieu de comparer
#   --keep               laisse le serveur tourner (sinon : supprimé, volumes compris)
#
# Démarre le serveur en Docker sous un projet compose dédié à la version,
# avec ses propres volumes, puis charge le seed de
# tests/integration/seed/ avec les seules commandes natives d'acryl-datahub,
# exporte le DataProduct, valide le Turtle contre la sensitivity shape, puis
# le compare par isomorphisme RDF à tests/integration/expected/.
#
# Jamais lancé en CI (ADR-0004 §3). Prérequis : Docker, ports 8080/9002/3306/
# 9092/9200 libres (arrêter tout autre quickstart DataHub avant), ~8 Go de RAM
# pour Docker.
#
# Isolation des données : le compose officiel du quickstart nomme ses volumes
# en dur (`datahub_mysqldata`, `datahub_osdata`, `datahub_broker`). Un autre
# nom de projet ne suffit donc PAS : un serveur d'une autre version démarrerait
# sur les données d'un quickstart existant. Le script télécharge ce compose,
# renomme les volumes au nom du projet, refuse de démarrer si un serveur répond
# déjà sur 8080, et vérifie les volumes montés avant toute écriture.
set -euo pipefail

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
  exit 2
}

version=""
update_reference=false
keep=false
for arg in "$@"; do
  case "$arg" in
    --update-reference) update_reference=true ;;
    --keep) keep=true ;;
    -h | --help) usage ;;
    -*) echo "Option inconnue : $arg" >&2; usage ;;
    *) [ -z "$version" ] && version="${arg#v}" || usage ;;
  esac
done
[ -n "$version" ] || usage

root="$(cd "$(dirname "$0")/.." && pwd)"
seed="$root/tests/integration/seed"
minor="$(echo "$version" | cut -d. -f1,2)"
reference="$root/tests/integration/expected/datahub-$minor.ttl"
dataproduct_urn="urn:li:dataProduct:dhhc-verify-venues"
work="$(mktemp -d)"

# Projet compose propre à la version : volumes et réseau isolés.
export DATAHUB_COMPOSE_PROJECT_NAME="dhhc-verify-${version//./-}"
# Toujours le serveur local, jamais ~/.datahubenv (qui peut viser un autre
# serveur) ; le quickstart n'active pas l'authentification.
export DATAHUB_GMS_URL="http://localhost:8080"
export DATAHUB_GMS_TOKEN=""
# Sortie redirigée sous Windows : sans UTF-8, le CLI datahub plante en
# affichant « ✔ » (cp1252). Seulement les flux standard : PYTHONUTF8 changerait
# aussi l'encodage des fichiers, et le CLI ne relirait plus son
# ~/.datahub/quickstart/.local-secrets.env, écrit dans l'encodage local.
export PYTHONIOENCODING=utf-8

step() { printf '\n== %s\n' "$*"; }
die() { echo "ERREUR : $*" >&2; exit 1; }

cleanup() {
  rm -rf "$work"
  if [ "$keep" = false ]; then
    step "Suppression du serveur $version (projet $DATAHUB_COMPOSE_PROJECT_NAME)"
    uv run --project "$root" datahub docker nuke || true
  else
    echo "Serveur laissé en marche. Arrêt : DATAHUB_COMPOSE_PROJECT_NAME=$DATAHUB_COMPOSE_PROJECT_NAME uv run datahub docker nuke"
  fi
}
trap cleanup EXIT

dh() { uv run --project "$root" datahub "$@"; }
dhhc() { uv run --project "$root" dh-healthdcat "$@"; }

if curl -sf -o /dev/null --max-time 5 "$DATAHUB_GMS_URL/health"; then
  trap - EXIT
  rm -rf "$work"
  die "un serveur DataHub répond déjà sur $DATAHUB_GMS_URL : l'arrêter avant le contrôle (aucune écriture faite)."
fi

step "Compose du quickstart $version, volumes renommés pour le projet $DATAHUB_COMPOSE_PROJECT_NAME"
# Même compose que `datahub docker quickstart --version` téléchargerait : sa
# table de versions peut viser une autre référence git que le tag (v1.7.0 →
# v1.7.0.1), dont le compose du tag ne démarre pas.
git_ref="$(uv run --project "$root" python -c "
from datahub.cli.quickstart_versioning import QuickstartVersionMappingConfig as Q
print(Q.fetch_quickstart_config().get_quickstart_execution_plan('v$version').composefile_git_ref)
" 2>/dev/null | tail -1)"
[ -n "$git_ref" ] || die "plan quickstart introuvable pour v$version"
compose="$work/docker-compose.yml"
curl -sfL -o "$compose" \
  "https://raw.githubusercontent.com/datahub-project/datahub/$git_ref/docker/quickstart/docker-compose.quickstart-profile.yml" \
  || die "compose introuvable pour $git_ref"
echo "Compose de la référence $git_ref"
sed -i "s/^    name: datahub_/    name: ${DATAHUB_COMPOSE_PROJECT_NAME}_/" "$compose"
if grep -q "name: datahub_" "$compose"; then
  die "volume datahub_* restant dans le compose : isolation impossible"
fi

step "Démarrage du serveur DataHub $version"
dh docker quickstart --version "v$version" --no-accept-version-default -f "$compose"

# Dernier garde-fou avant toute écriture : MySQL doit monter le volume du projet.
mounts="$(docker inspect "$DATAHUB_COMPOSE_PROJECT_NAME-mysql-1" --format '{{range .Mounts}}{{.Name}} {{end}}')"
case "$mounts" in
  *"${DATAHUB_COMPOSE_PROJECT_NAME}_mysqldata"*) ;;
  *) die "MySQL monte « $mounts », pas le volume du projet : arrêt avant toute écriture." ;;
esac

step "Seed : définitions des structured properties"
dh properties upsert -f "$seed/structured-properties.yml"

step "Seed : Datasets, profil et valeurs des SP (MCP JSON)"
# Chemin relatif : sous Windows, la source `file` lit « C: » comme un schéma d'URL.
(cd "$root" && dh ingest mcps tests/integration/seed/metadata.json)

step "Seed : DataProduct"
dh dataproduct upsert -f "$seed/dataproduct.yml"

step "Export"
dhhc export-file --urn "$dataproduct_urn" --output "$work/export.ttl" --base-uri https://example.org

step "Validation SHACL (sensitivity shape)"
dhhc validate "$work/export.ttl"

if [ "$update_reference" = true ]; then
  step "Réécriture de la référence $minor"
  uv run --project "$root" python "$root/scripts/compare_reference.py" \
    "$work/export.ttl" "$reference" --update
else
  step "Comparaison à la référence $minor"
  uv run --project "$root" python "$root/scripts/compare_reference.py" \
    "$work/export.ttl" "$reference"
fi
