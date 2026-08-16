"""Pipeline unifié : lecture -> mapping -> rapport d'issues -> validation
SHACL -> décision. Seam unique traversé par `export-file`, `push-hdh` et les
tests (spec/spec-feature-export-pipeline.md) — `cli.py` ne fait plus que
traduire les outcomes produits ici en présentation terminal.

`prepare()` produit une séquence d'outcomes typés, un par DataProduct
sélectionné :

- `Prepared` — jeu prêt à être écrit ou poussé (pivot + graphe RDF + rapport
  SHACL, y compris quand ce rapport est non conforme sous `strict=False`).
- `Unreadable` — le DataProduct n'a pas de nom exploitable côté DataHub
  (DataProduct invalide ou introuvable, `read_data_product` a levé
  `ValueError`). Exclu dans tous les cas : il n'y a pas de graphe à écrire.
- `Rejected` — lisible, mais erreurs de pivot et/ou non-conformité SHACL, sous
  `strict=True`.

`strict` est le seul paramètre qui porte la politique d'exclusion : c'est ce
qui distingue `export-file` (`--strict/--no-strict`) de `push-hdh` (toujours
`strict=True`, jamais de `--no-strict` — ne pas envoyer de données invalides
au HDH est une propriété de sûreté, pas une préférence configurable).

Attention : `dataset_to_graph()` enrichit `dataset.issues` en place
(mapping/dataset.py). Chaque DataProduct n'est donc mappé qu'une seule fois
ici — un second appel dupliquerait chaque issue ERROR."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Iterator, Union

from rdflib import Graph

from dh_healthdcat.emit.hdh_client import HdhClientError, HdhTarget
from dh_healthdcat.emit.state import PushState
from dh_healthdcat.mapping.dataset import dataset_to_graph
from dh_healthdcat.model import HealthDataset
from dh_healthdcat.reader.dataproduct import DEFAULT_BASE_URI, read_data_product
from dh_healthdcat.reader.graph import ReadContext
from dh_healthdcat.validate.shacl import ShaclResult, validate_graph


@dataclass(frozen=True, slots=True)
class Prepared:
    """Jeu prêt à être écrit (export-file) ou poussé (push-hdh)."""

    urn: str
    dataset: HealthDataset
    graph: Graph
    shacl: ShaclResult


@dataclass(frozen=True, slots=True)
class Unreadable:
    """Le DataProduct n'a pas de dataProductProperties.name exploitable côté
    DataHub — invalide ou introuvable."""

    urn: str
    reason: str


@dataclass(frozen=True, slots=True)
class Rejected:
    """Lisible mais invalide : erreurs de pivot et/ou non-conformité SHACL,
    exclu par la politique stricte."""

    urn: str
    dataset: HealthDataset
    shacl: ShaclResult


Outcome = Union[Prepared, Unreadable, Rejected]


def prepare(
    ctx: ReadContext,
    urns: Iterable[str],
    *,
    base_uri: str = DEFAULT_BASE_URI,
    strict: bool = True,
) -> Iterator[Outcome]:
    for urn in urns:
        try:
            dataset = read_data_product(ctx, urn, base_uri=base_uri)
        except ValueError as exc:
            yield Unreadable(urn=urn, reason=str(exc))
            continue

        graph = dataset_to_graph(dataset)
        shacl = validate_graph(graph)

        # Un DataProduct invalide est exclu de l'export, pas le lot entier :
        # les autres jeux sélectionnés ne doivent pas payer pour celui-ci
        # (voir investigation --tag aphp:access, qui a fait échouer un export
        # entier à cause de DataProducts de production sans rapport avec le
        # filtre, jamais peuplés en propriétés HealthDCAT-AP).
        if strict and (dataset.has_errors or not shacl.conforms):
            yield Rejected(urn=urn, dataset=dataset, shacl=shacl)
            continue

        yield Prepared(urn=urn, dataset=dataset, graph=graph, shacl=shacl)


class PushAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"


@dataclass(frozen=True, slots=True)
class Pushed:
    """Jeu effectivement créé ou mis à jour au HDH ; l'id est déjà persisté
    dans `PushState` au moment où cet outcome est émis."""

    urn: str
    dataset: HealthDataset
    action: PushAction
    hdh_id: str


@dataclass(frozen=True, slots=True)
class Planned:
    """`--dry-run` : ce qui serait créé/mis à jour, sans appel réseau
    d'écriture ni mutation de l'état."""

    urn: str
    dataset: HealthDataset
    action: PushAction
    existing_id: str | None
    turtle_bytes: int


@dataclass(frozen=True, slots=True)
class PushFailed:
    """Échec HDH (statut d'erreur ou de transport) sur ce jeu précis ; les
    jeux suivants du lot ne sont pas affectés (story 13)."""

    urn: str
    dataset: HealthDataset
    error: str


PushOutcome = Union[Pushed, Planned, PushFailed, Unreadable, Rejected]


def push(
    ctx: ReadContext,
    urns: Iterable[str],
    *,
    target: HdhTarget,
    state: PushState,
    base_uri: str = DEFAULT_BASE_URI,
    dry_run: bool = False,
) -> Iterator[PushOutcome]:
    """Créer ou mettre à jour chaque jeu préparé, puis enregistrer l'id
    aussitôt (persistance immédiate — story 8/12/18). Ne pousse jamais un jeu
    invalide : consomme `prepare(strict=True)`, politique fixée à un seul
    endroit (`push-hdh` n'expose pas de `--no-strict`, story 9)."""

    for outcome in prepare(ctx, urns, base_uri=base_uri, strict=True):
        if not isinstance(outcome, Prepared):
            yield outcome
            continue

        turtle = outcome.graph.serialize(format="turtle")
        existing_id = state.hdh_id_for(outcome.urn)
        action = PushAction.UPDATED if existing_id else PushAction.CREATED

        if dry_run:
            yield Planned(
                urn=outcome.urn,
                dataset=outcome.dataset,
                action=action,
                existing_id=existing_id,
                turtle_bytes=len(turtle.encode("utf-8")),
            )
            continue

        try:
            if existing_id:
                hdh_id = target.update_dataset(existing_id, turtle)
            else:
                hdh_id = target.create_dataset(turtle)
        except HdhClientError as exc:
            yield PushFailed(urn=outcome.urn, dataset=outcome.dataset, error=str(exc))
            continue

        state.record(outcome.urn, hdh_id)
        yield Pushed(urn=outcome.urn, dataset=outcome.dataset, action=action, hdh_id=hdh_id)
