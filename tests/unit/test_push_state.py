"""État de poussée (emit/state.py) — spec/spec-feature-export-pipeline.md et
spec/spec-feature-catalogue-instance-config.md (cloisonnement par instance,
REQ-008/009).

`PushState` remplace les cinq fonctions de module par un objet qui possède son
chemin et persiste immédiatement à chaque `record()`, en écriture atomique
(fichier temporaire + `os.replace`). C'est ce qui rend une poussée interrompue
reprenable sans duplication (G1/story 8, 12, 18)."""

from __future__ import annotations

import json

from dh_healthdcat.emit.state import PushState

INSTANCE_A = "https://a.test"
INSTANCE_B = "https://b.test"


def test_open_on_missing_path_is_empty(tmp_path):
    state = PushState.open(tmp_path / "state.json", instance=INSTANCE_A)

    assert state.hdh_id_for("urn:li:dataProduct:a") is None


def test_record_persists_immediately_visible_on_reopen(tmp_path):
    path = tmp_path / "state.json"
    state = PushState.open(path, instance=INSTANCE_A)

    state.record("urn:li:dataProduct:a", "hdh-id-1")

    reopened = PushState.open(path, instance=INSTANCE_A)
    assert reopened.hdh_id_for("urn:li:dataProduct:a") == "hdh-id-1"


def test_each_record_is_durable_without_waiting_for_the_batch_to_finish(tmp_path):
    """G3/story 12/18 : rouvrir l'état après chaque enregistrement, pas
    seulement à la fin du lot — reproduit une reprise après interruption."""

    path = tmp_path / "state.json"
    state = PushState.open(path, instance=INSTANCE_A)

    state.record("urn:li:dataProduct:a", "hdh-id-1")
    assert PushState.open(path, instance=INSTANCE_A).hdh_id_for("urn:li:dataProduct:a") == "hdh-id-1"

    state.record("urn:li:dataProduct:b", "hdh-id-2")
    reopened = PushState.open(path, instance=INSTANCE_A)
    assert reopened.hdh_id_for("urn:li:dataProduct:a") == "hdh-id-1"
    assert reopened.hdh_id_for("urn:li:dataProduct:b") == "hdh-id-2"


def test_record_overwrites_existing_id_for_the_same_urn(tmp_path):
    path = tmp_path / "state.json"
    state = PushState.open(path, instance=INSTANCE_A)

    state.record("urn:li:dataProduct:a", "hdh-id-1")
    state.record("urn:li:dataProduct:a", "hdh-id-2")

    assert PushState.open(path, instance=INSTANCE_A).hdh_id_for("urn:li:dataProduct:a") == "hdh-id-2"


def test_record_leaves_no_leftover_temp_file(tmp_path):
    path = tmp_path / "state.json"
    state = PushState.open(path, instance=INSTANCE_A)

    state.record("urn:li:dataProduct:a", "hdh-id-1")

    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]


def test_record_writes_the_versioned_instance_partitioned_shape(tmp_path):
    """Format sur disque (REQ-008) : `{"version": 2, "instances": {url: {urn:
    id}}}`, indent=2, clés triées, non-ASCII préservé."""

    path = tmp_path / "state.json"
    state = PushState.open(path, instance=INSTANCE_A)

    state.record("urn:li:dataProduct:b", "id-b")
    state.record("urn:li:dataProduct:a", "id-a")

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == {"version": 2, "instances": {INSTANCE_A: {"urn:li:dataProduct:a": "id-a", "urn:li:dataProduct:b": "id-b"}}}
    assert path.read_text(encoding="utf-8") == json.dumps(on_disk, indent=2, sort_keys=True, ensure_ascii=False)


def test_open_creates_parent_directories_lazily_on_first_record(tmp_path):
    path = tmp_path / "nested" / "dir" / "state.json"
    state = PushState.open(path, instance=INSTANCE_A)

    state.record("urn:li:dataProduct:a", "hdh-id-1")

    assert path.exists()


class TestPartitioning:
    """REQ-008 : les ids attribués par une instance ne doivent jamais être
    visibles — ni réutilisables — depuis une autre."""

    def test_id_recorded_for_one_instance_is_invisible_from_another(self, tmp_path):
        path = tmp_path / "state.json"
        state_a = PushState.open(path, instance=INSTANCE_A)
        state_a.record("urn:li:dataProduct:a", "id-from-a")

        state_b = PushState.open(path, instance=INSTANCE_B)

        assert state_b.hdh_id_for("urn:li:dataProduct:a") is None

    def test_recording_for_one_instance_does_not_touch_the_others_bucket(self, tmp_path):
        path = tmp_path / "state.json"
        state_a = PushState.open(path, instance=INSTANCE_A)
        state_a.record("urn:li:dataProduct:a", "id-from-a")

        state_b = PushState.open(path, instance=INSTANCE_B)
        state_b.record("urn:li:dataProduct:x", "id-from-b")

        on_disk = json.loads(path.read_text(encoding="utf-8"))
        assert on_disk["instances"][INSTANCE_A] == {"urn:li:dataProduct:a": "id-from-a"}
        assert on_disk["instances"][INSTANCE_B] == {"urn:li:dataProduct:x": "id-from-b"}


class TestFlatFormatMigration:
    """REQ-009 : reprise transparente d'un fichier d'état pré-instance, sans
    effet de bord tant qu'aucun `record()` n'a eu lieu."""

    def _write_flat_state(self, path):
        path.write_text(json.dumps({"urn:li:dataProduct:a": "legacy-id"}), encoding="utf-8")

    def test_ids_are_visible_under_the_current_instance(self, tmp_path):
        path = tmp_path / "state.json"
        self._write_flat_state(path)

        state = PushState.open(path, instance=INSTANCE_A)

        assert state.hdh_id_for("urn:li:dataProduct:a") == "legacy-id"

    def test_warning_names_the_instance_and_the_count_exactly_once(self, tmp_path):
        path = tmp_path / "state.json"
        self._write_flat_state(path)
        warnings: list[str] = []

        PushState.open(path, instance=INSTANCE_A, on_warning=warnings.append)

        assert len(warnings) == 1
        assert INSTANCE_A in warnings[0]
        assert "1" in warnings[0]

    def test_file_is_byte_for_byte_unchanged_until_the_first_record(self, tmp_path):
        path = tmp_path / "state.json"
        self._write_flat_state(path)
        before = path.read_bytes()

        PushState.open(path, instance=INSTANCE_A, on_warning=lambda m: None)

        assert path.read_bytes() == before

    def test_first_record_rewrites_the_file_in_versioned_format(self, tmp_path):
        path = tmp_path / "state.json"
        self._write_flat_state(path)
        state = PushState.open(path, instance=INSTANCE_A, on_warning=lambda m: None)

        state.record("urn:li:dataProduct:new", "new-id")

        on_disk = json.loads(path.read_text(encoding="utf-8"))
        assert on_disk == {
            "version": 2,
            "instances": {INSTANCE_A: {"urn:li:dataProduct:a": "legacy-id", "urn:li:dataProduct:new": "new-id"}},
        }

    def test_no_warning_when_flat_file_is_empty(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text("{}", encoding="utf-8")
        warnings: list[str] = []

        PushState.open(path, instance=INSTANCE_A, on_warning=warnings.append)

        assert warnings == []
