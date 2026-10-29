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
# avec ses propres volumes, puis charge les définitions des SP
# (`dh-healthdcat properties`) et le seed de tests/integration/seed/ avec les
# seules commandes natives d'acryl-datahub,
# exporte le DataProduct, valide le Turtle contre la sensitivity shape, puis
# le compare par isomorphisme RDF à tests/integration/expected/.
#
# Jamais lancé en CI (ADR-0004 §3). Prérequis : Docker, ports 8080/9002/3306/
# 9092/9200 libres (arrêter tout autre quickstart DataHub avant), ~8 Go de RAM
# pour Docker.
#
# Isolation des données : volumes propres au projet `dhhc-verify-<version>`,
# voir scripts/lib/datahub-isolation.sh.
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
# shellcheck source=lib/datahub-isolation.sh
. "$root/scripts/lib/datahub-isolation.sh"
seed="$root/tests/integration/seed"
minor="$(echo "$version" | cut -d. -f1,2)"
reference="$root/tests/integration/expected/datahub-$minor.ttl"
dataproduct_urn="urn:li:dataProduct:dhhc-verify-venues"
work="$(mktemp -d)"

isolation_env "dhhc-verify-${version//./-}"

cleanup() {
  rm -rf "$work"
  if [ "$keep" = false ]; then
    step "Suppression du serveur $version (projet $DATAHUB_COMPOSE_PROJECT_NAME)"
    purge_isolated || true
  else
    echo "Serveur laissé en marche. Arrêt : scripts/datahub-local.sh $version down --purge --project $DATAHUB_COMPOSE_PROJECT_NAME"
  fi
}
trap cleanup EXIT

dhhc() { uv run --project "$root" dh-healthdcat "$@"; }

if gms_up; then
  trap - EXIT
  rm -rf "$work"
  die "un serveur DataHub répond déjà sur $DATAHUB_GMS_URL : l'arrêter avant le contrôle (aucune écriture faite)."
fi

compose="$work/docker-compose.yml"
fetch_isolated_compose "$version" "$compose"
start_isolated "$version" "$compose"

step "Seed : définitions des structured properties"
# Les définitions canoniques du paquet (#134), pas une copie : le contrôle
# vérifie aussi qu'`upsert` les accepte sur cette version du serveur.
dhhc properties --output "$work/structured-properties.yml"
dh properties upsert -f "$work/structured-properties.yml"

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
