"""pipeline.push — spec/spec-feature-export-pipeline.md.

La poussée (créer ou mettre à jour, puis enregistrer l'id) fait partie du
pipeline, pas de la CLI : c'est cette séquence précise qui porte le risque de
duplication en cas d'interruption. `push()` consomme `prepare(strict=True)` —
`push-hdh` n'expose pas de `--no-strict` : ne jamais envoyer de données
invalides au HDH est une propriété de sûreté, pas une préférence."""

from __future__ import annotations

from dh_healthdcat.emit.state import PushState
from dh_healthdcat.pipeline import (
    Planned,
    PushAction,
    Pushed,
    PushFailed,
    Rejected,
    Unreadable,
    push,
)
from tests.fixtures.fake_datahub import (
    DATAPRODUCT_URN,
    NONCONFORMING_DATAPRODUCT_URN,
    UNREADABLE_DATAPRODUCT_URN,
    build_context,
)
from tests.fixtures.fake_hdh import InMemoryHdhCatalog


def test_new_dataproduct_is_created_and_id_recorded(tmp_path):
    ctx = build_context()
    target = InMemoryHdhCatalog()
    state = PushState.open(tmp_path / "state.json", instance="https://hdh.test")

    [outcome] = list(push(ctx, [DATAPRODUCT_URN], target=target, state=state))

    assert isinstance(outcome, Pushed)
    assert outcome.action is PushAction.CREATED
    assert len(target.created) == 1
    assert target.updated == []
    assert state.hdh_id_for(DATAPRODUCT_URN) == outcome.hdh_id


def test_already_known_dataproduct_is_updated_not_recreated(tmp_path):
    ctx = build_context()
    target = InMemoryHdhCatalog()
    state = PushState.open(tmp_path / "state.json", instance="https://hdh.test")
    state.record(DATAPRODUCT_URN, "existing-hdh-id")

    [outcome] = list(push(ctx, [DATAPRODUCT_URN], target=target, state=state))

    assert isinstance(outcome, Pushed)
    assert outcome.action is PushAction.UPDATED
    assert outcome.hdh_id == "existing-hdh-id"
    assert target.created == []
    assert len(target.updated) == 1
    assert target.updated[0][0] == "existing-hdh-id"


def test_each_push_is_durable_without_waiting_for_the_batch_to_finish(tmp_path):
    """story 8/12/18 : rouvrir l'état après chaque jeu poussé, pas seulement
    à la fin du lot — reproduit une reprise après interruption."""

    ctx = build_context()
    target = InMemoryHdhCatalog()
    path = tmp_path / "state.json"
    state = PushState.open(path, instance="https://hdh.test")

    [outcome] = list(push(ctx, [DATAPRODUCT_URN], target=target, state=state))

    reopened = PushState.open(path, instance="https://hdh.test")
    assert reopened.hdh_id_for(DATAPRODUCT_URN) == outcome.hdh_id


def test_invalid_dataproduct_produces_no_write_call(tmp_path):
    """story 9 : un jeu invalide n'est jamais envoyé au HDH, même sous
    push-hdh qui n'expose pas --no-strict."""

    ctx = build_context()
    target = InMemoryHdhCatalog()
    state = PushState.open(tmp_path / "state.json", instance="https://hdh.test")

    [outcome] = list(push(ctx, [NONCONFORMING_DATAPRODUCT_URN], target=target, state=state))

    assert isinstance(outcome, Rejected)
    assert target.created == []
    assert target.updated == []


def test_unreadable_dataproduct_is_relayed_with_no_write_call(tmp_path):
    ctx = build_context()
    target = InMemoryHdhCatalog()
    state = PushState.open(tmp_path / "state.json", instance="https://hdh.test")

    [outcome] = list(push(ctx, [UNREADABLE_DATAPRODUCT_URN], target=target, state=state))

    assert isinstance(outcome, Unreadable)
    assert target.created == []
    assert target.updated == []


def test_dry_run_plans_without_any_write_call_or_state_mutation(tmp_path):
    ctx = build_context()
    target = InMemoryHdhCatalog()
    state = PushState.open(tmp_path / "state.json", instance="https://hdh.test")

    [outcome] = list(push(ctx, [DATAPRODUCT_URN], target=target, state=state, dry_run=True))

    assert isinstance(outcome, Planned)
    assert outcome.action is PushAction.CREATED
    assert outcome.existing_id is None
    assert outcome.turtle_bytes > 0
    assert target.created == []
    assert target.updated == []
    assert state.hdh_id_for(DATAPRODUCT_URN) is None


def test_dry_run_plans_an_update_when_a_known_id_exists(tmp_path):
    ctx = build_context()
    target = InMemoryHdhCatalog()
    state = PushState.open(tmp_path / "state.json", instance="https://hdh.test")
    state.record(DATAPRODUCT_URN, "existing-hdh-id")

    [outcome] = list(push(ctx, [DATAPRODUCT_URN], target=target, state=state, dry_run=True))

    assert isinstance(outcome, Planned)
    assert outcome.action is PushAction.UPDATED
    assert outcome.existing_id == "existing-hdh-id"


def test_a_failed_push_does_not_prevent_the_next_dataproduct(tmp_path):
    """story 13 : un échec réseau sur un jeu n'empêche pas les jeux suivants
    d'être poussés. Le même DataProduct valide est poussé deux fois de suite
    (deux appels indépendants create_dataset) : le premier échoue, le second
    doit tout de même passer."""

    ctx = build_context()
    target = InMemoryHdhCatalog(fail_next_creates=1)
    state = PushState.open(tmp_path / "state.json", instance="https://hdh.test")

    outcomes = list(push(ctx, [DATAPRODUCT_URN, DATAPRODUCT_URN], target=target, state=state))

    assert len(outcomes) == 2
    assert isinstance(outcomes[0], PushFailed)
    assert isinstance(outcomes[1], Pushed)
    assert len(target.created) == 1
    assert state.hdh_id_for(DATAPRODUCT_URN) == outcomes[1].hdh_id
