"""État de poussée (emit/state.py) — spec/spec-feature-export-pipeline.md.

`PushState` remplace les cinq fonctions de module par un objet qui possède son
chemin et persiste immédiatement à chaque `record()`, en écriture atomique
(fichier temporaire + `os.replace`). C'est ce qui rend une poussée interrompue
reprenable sans duplication (G1/story 8, 12, 18)."""

from __future__ import annotations

import json

from dh_healthdcat.emit.state import PushState


def test_open_on_missing_path_is_empty(tmp_path):
    state = PushState.open(tmp_path / "state.json")

    assert state.hdh_id_for("urn:li:dataProduct:a") is None


def test_record_persists_immediately_visible_on_reopen(tmp_path):
    path = tmp_path / "state.json"
    state = PushState.open(path)

    state.record("urn:li:dataProduct:a", "hdh-id-1")

    reopened = PushState.open(path)
    assert reopened.hdh_id_for("urn:li:dataProduct:a") == "hdh-id-1"


def test_each_record_is_durable_without_waiting_for_the_batch_to_finish(tmp_path):
    """G3/story 12/18 : rouvrir l'état après chaque enregistrement, pas
    seulement à la fin du lot — reproduit une reprise après interruption."""

    path = tmp_path / "state.json"
    state = PushState.open(path)

    state.record("urn:li:dataProduct:a", "hdh-id-1")
    assert PushState.open(path).hdh_id_for("urn:li:dataProduct:a") == "hdh-id-1"

    state.record("urn:li:dataProduct:b", "hdh-id-2")
    reopened = PushState.open(path)
    assert reopened.hdh_id_for("urn:li:dataProduct:a") == "hdh-id-1"
    assert reopened.hdh_id_for("urn:li:dataProduct:b") == "hdh-id-2"


def test_record_overwrites_existing_id_for_the_same_urn(tmp_path):
    path = tmp_path / "state.json"
    state = PushState.open(path)

    state.record("urn:li:dataProduct:a", "hdh-id-1")
    state.record("urn:li:dataProduct:a", "hdh-id-2")

    assert PushState.open(path).hdh_id_for("urn:li:dataProduct:a") == "hdh-id-2"


def test_record_leaves_no_leftover_temp_file(tmp_path):
    path = tmp_path / "state.json"
    state = PushState.open(path)

    state.record("urn:li:dataProduct:a", "hdh-id-1")

    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]


def test_record_writes_the_same_json_shape_as_before(tmp_path):
    """Non-régression du format sur disque : mapping plat URN -> id,
    indent=2, clés triées, non-ASCII préservé."""

    path = tmp_path / "state.json"
    state = PushState.open(path)

    state.record("urn:li:dataProduct:b", "id-b")
    state.record("urn:li:dataProduct:a", "id-a")

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == {"urn:li:dataProduct:a": "id-a", "urn:li:dataProduct:b": "id-b"}
    assert path.read_text(encoding="utf-8") == json.dumps(on_disk, indent=2, sort_keys=True, ensure_ascii=False)


def test_open_creates_parent_directories_lazily_on_first_record(tmp_path):
    path = tmp_path / "nested" / "dir" / "state.json"
    state = PushState.open(path)

    state.record("urn:li:dataProduct:a", "hdh-id-1")

    assert path.exists()
