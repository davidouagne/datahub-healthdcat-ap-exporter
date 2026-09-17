"""cli.py — corps des commandes `export-file`/`validate`/`push-hdh` une fois
`--config`/la clé résolus (test_cli_push_config.py ne couvre que les sorties
d'erreur *antérieures à tout appel réseau*). `dh_healthdcat.cli.from_env` est
monkeypatché vers `tests/fixtures/fake_datahub.py::build_context` (hors
ligne, pas d'instance DataHub) ; `HdhClient.whoami`/`create_dataset`/
`update_dataset` sont monkeypatchés au niveau classe (pas de réseau HDH) —
jusqu'ici jamais exercés par la suite (issue #79)."""

from __future__ import annotations

from rdflib import Graph
from typer.testing import CliRunner

import dh_healthdcat.cli as cli_module
from dh_healthdcat.emit.hdh_client import HdhClient, HdhClientError
from dh_healthdcat.emit.state import PushState
from dh_healthdcat.reader.graph import ReadContext
from tests.fixtures.fake_datahub import (
    DATAPRODUCT_URN,
    NONCONFORMING_DATAPRODUCT_URN,
    build_context,
)

runner = CliRunner()


def _write_config(tmp_path, content: str = "profiles: {}\n"):
    path = tmp_path / "config.yml"
    path.write_text(content, encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# export-file
# --------------------------------------------------------------------------


def test_export_file_writes_a_valid_dataproduct(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "from_env", build_context)
    output = tmp_path / "out.ttl"

    result = runner.invoke(
        cli_module.app, ["export-file", "--output", str(output), "--urn", DATAPRODUCT_URN]
    )

    assert result.exit_code == 0, result.output
    assert output.is_file()
    graph = Graph().parse(str(output), format="turtle")
    assert len(graph) > 0
    assert "Écrit" in result.output


def test_export_file_default_selection_mixes_outcomes_and_exits_1(tmp_path, monkeypatch):
    """Sans --urn : les trois DataProducts de build_context() (valide,
    illisible, non conforme) — cf. IGNORÉ/exclu/"Écrit" dans le même run."""

    monkeypatch.setattr(cli_module, "from_env", build_context)
    output = tmp_path / "out.ttl"

    result = runner.invoke(cli_module.app, ["export-file", "--output", str(output)])

    assert result.exit_code == 1
    assert "IGNORÉ" in result.output  # DataProduct illisible
    assert "non conforme SHACL" in result.output  # DataProduct non conforme
    assert "exclu de l'export" in result.output
    assert output.is_file()  # le jeu valide, lui, a bien été écrit
    assert "2 exclu(s)" in result.output


def test_export_file_nothing_valid_writes_no_file_and_exits_1(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "from_env", build_context)
    output = tmp_path / "out.ttl"

    result = runner.invoke(
        cli_module.app,
        ["export-file", "--output", str(output), "--urn", NONCONFORMING_DATAPRODUCT_URN],
    )

    assert result.exit_code == 1
    assert "Export non écrit" in result.output
    assert not output.exists()


def test_export_file_split_per_dataset_writes_one_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "from_env", build_context)
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    result = runner.invoke(
        cli_module.app,
        [
            "export-file",
            "--output",
            str(out_dir),
            "--urn",
            DATAPRODUCT_URN,
            "--split-per-dataset",
        ],
    )

    assert result.exit_code == 0, result.output
    written = list(out_dir.glob("*.ttl"))
    assert len(written) == 1
    assert "jeu(x) écrit(s)" in result.output


def test_export_file_urn_with_tag_triggers_the_precedence_warning(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "from_env", build_context)
    output = tmp_path / "out.ttl"

    result = runner.invoke(
        cli_module.app,
        ["export-file", "--output", str(output), "--urn", DATAPRODUCT_URN, "--tag", "eds"],
    )

    assert "--urn est prioritaire" in result.output


def test_export_file_invalid_tag_mode_exits_2(monkeypatch):
    monkeypatch.setattr(cli_module, "from_env", build_context)

    result = runner.invoke(
        cli_module.app,
        [
            "export-file",
            "--output",
            "unused.ttl",
            "--tag",
            "eds",
            "--tag-mode",
            "bogus",
        ],
    )

    assert result.exit_code == 2
    assert "tag_mode invalide" in result.output


def test_export_file_no_match_exits_1_and_writes_nothing(tmp_path, monkeypatch):
    class _EmptyGraph:
        def get_urns_by_filter(self, *, entity_types=None, extra_or_filters=None):
            return []

    monkeypatch.setattr(cli_module, "from_env", lambda: ReadContext(graph=_EmptyGraph()))
    output = tmp_path / "out.ttl"

    result = runner.invoke(
        cli_module.app, ["export-file", "--output", str(output), "--domain", "eds"]
    )

    assert result.exit_code == 1
    assert "Aucun DataProduct ne correspond" in result.output
    assert not output.exists()


# --------------------------------------------------------------------------
# validate
# --------------------------------------------------------------------------


def test_validate_conformant_file_exits_0(tmp_path):
    path = tmp_path / "empty.ttl"
    path.write_text("# graphe vide : conforme trivialement\n", encoding="utf-8")

    result = runner.invoke(cli_module.app, ["validate", str(path)])

    assert result.exit_code == 0
    assert "Conforme" in result.output


def test_validate_nonconformant_file_exits_1(tmp_path):
    path = tmp_path / "invalid.ttl"
    path.write_text(
        "@prefix dcat: <http://www.w3.org/ns/dcat#> .\n<urn:test:dataset> a dcat:Dataset .\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli_module.app, ["validate", str(path)])

    assert result.exit_code == 1
    assert "Non conforme" in result.output


def test_validate_unparseable_file_exits_2(tmp_path):
    path = tmp_path / "broken.ttl"
    path.write_text("ceci n'est pas du turtle valide {{{", encoding="utf-8")

    result = runner.invoke(cli_module.app, ["validate", str(path)])

    assert result.exit_code == 2
    assert "Impossible de lire" in result.output


def test_validate_explicit_format_overrides_extension_based_detection(tmp_path):
    path = tmp_path / "data.export"  # extension non reconnue par rdflib
    path.write_text(
        "<urn:test:dataset> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
        "<http://www.w3.org/ns/dcat#Dataset> .\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli_module.app, ["validate", str(path), "--format", "n-triples"])

    assert result.exit_code in (0, 1)  # peu importe la conformité : ce qui compte, c'est le parse
    assert "Impossible de lire" not in result.output


# --------------------------------------------------------------------------
# push-hdh
# --------------------------------------------------------------------------


def test_push_hdh_creates_a_new_dataproduct(tmp_path, monkeypatch):
    config = _write_config(tmp_path)
    monkeypatch.setattr(cli_module, "from_env", build_context)
    monkeypatch.setattr(HdhClient, "whoami", lambda self: {"role": "data-provider"})
    created = []
    monkeypatch.setattr(
        HdhClient,
        "create_dataset",
        lambda self, turtle: created.append(turtle) or "hdh-new-1",
    )

    result = runner.invoke(
        cli_module.app,
        [
            "push-hdh",
            "--hdh-url",
            "https://hdh.test",
            "--api-key",
            "mdc_x",
            "--config",
            str(config),
            "--urn",
            DATAPRODUCT_URN,
            "--state-file",
            str(tmp_path / "state.json"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(created) == 1
    assert "créé" in result.output
    assert "Connecté à https://hdh.test" in result.output


def test_push_hdh_dry_run_never_calls_create_dataset(tmp_path, monkeypatch):
    config = _write_config(tmp_path)
    monkeypatch.setattr(cli_module, "from_env", build_context)
    monkeypatch.setattr(HdhClient, "whoami", lambda self: {"role": "data-provider"})

    def _fail(self, *a, **kw):
        raise AssertionError("create_dataset ne doit pas être appelé en --dry-run")

    monkeypatch.setattr(HdhClient, "create_dataset", _fail)

    result = runner.invoke(
        cli_module.app,
        [
            "push-hdh",
            "--hdh-url",
            "https://hdh.test",
            "--api-key",
            "mdc_x",
            "--config",
            str(config),
            "--urn",
            DATAPRODUCT_URN,
            "--state-file",
            str(tmp_path / "state.json"),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "[dry-run]" in result.output


def test_push_hdh_updates_a_known_dataproduct(tmp_path, monkeypatch):
    config = _write_config(tmp_path)
    state_path = tmp_path / "state.json"
    PushState.open(state_path, instance="https://hdh.test").record(DATAPRODUCT_URN, "existing-id")
    monkeypatch.setattr(cli_module, "from_env", build_context)
    monkeypatch.setattr(HdhClient, "whoami", lambda self: {"role": "data-provider"})
    monkeypatch.setattr(HdhClient, "update_dataset", lambda self, original_id, turtle: original_id)

    result = runner.invoke(
        cli_module.app,
        [
            "push-hdh",
            "--hdh-url",
            "https://hdh.test",
            "--api-key",
            "mdc_x",
            "--config",
            str(config),
            "--urn",
            DATAPRODUCT_URN,
            "--state-file",
            str(state_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "mis à jour" in result.output


def test_push_hdh_default_selection_reports_unreadable_and_rejected(tmp_path, monkeypatch):
    config = _write_config(tmp_path)
    monkeypatch.setattr(cli_module, "from_env", build_context)
    monkeypatch.setattr(HdhClient, "whoami", lambda self: {"role": "data-provider"})
    monkeypatch.setattr(HdhClient, "create_dataset", lambda self, turtle: "hdh-new-1")

    result = runner.invoke(
        cli_module.app,
        [
            "push-hdh",
            "--hdh-url",
            "https://hdh.test",
            "--api-key",
            "mdc_x",
            "--config",
            str(config),
            "--state-file",
            str(tmp_path / "state.json"),
        ],
    )

    assert result.exit_code == 1
    assert "IGNORÉ" in result.output  # DataProduct illisible
    assert "invalide" in result.output  # DataProduct non conforme rejeté


def test_push_hdh_push_failure_does_not_abort_and_exits_1(tmp_path, monkeypatch):
    config = _write_config(tmp_path)
    monkeypatch.setattr(cli_module, "from_env", build_context)
    monkeypatch.setattr(HdhClient, "whoami", lambda self: {"role": "data-provider"})

    def _fail(self, turtle):
        raise HdhClientError(500, "échec simulé")

    monkeypatch.setattr(HdhClient, "create_dataset", _fail)

    result = runner.invoke(
        cli_module.app,
        [
            "push-hdh",
            "--hdh-url",
            "https://hdh.test",
            "--api-key",
            "mdc_x",
            "--config",
            str(config),
            "--urn",
            DATAPRODUCT_URN,
            "--state-file",
            str(tmp_path / "state.json"),
        ],
    )

    assert result.exit_code == 1
    assert "ÉCHEC" in result.output


def test_push_hdh_invalid_api_key_exits_1_before_any_selection(tmp_path, monkeypatch):
    config = _write_config(tmp_path)

    def _unauthorized(self):
        raise HdhClientError(401, "clé invalide")

    monkeypatch.setattr(HdhClient, "whoami", _unauthorized)

    result = runner.invoke(
        cli_module.app,
        [
            "push-hdh",
            "--hdh-url",
            "https://hdh.test",
            "--api-key",
            "mdc_bad",
            "--config",
            str(config),
            "--state-file",
            str(tmp_path / "state.json"),
        ],
    )

    assert result.exit_code == 1
    assert "Clé API invalide" in result.output


# --------------------------------------------------------------------------
# main()
# --------------------------------------------------------------------------


def test_main_runs_the_typer_app(monkeypatch):
    import pytest

    monkeypatch.setattr("sys.argv", ["dh-healthdcat", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        cli_module.main()
    assert exc_info.value.code == 0
