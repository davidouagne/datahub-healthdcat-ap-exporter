"""URI de base obligatoire côté CLI (#136, ADR-0005 §4) : résolue avant tout
appel réseau, depuis `--base-uri` ou le profil. `--config` est toujours
explicite (REQ-011)."""

from __future__ import annotations

from rdflib import Graph, URIRef
from typer.testing import CliRunner

import dh_healthdcat.cli as cli_module
from dh_healthdcat.mapping.namespaces import DCT
from tests.fixtures.fake_datahub import DATAPRODUCT_URN, build_context

runner = CliRunner()


def _empty_config(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text("profiles: {}\n", encoding="utf-8")
    return path


def test_export_without_base_uri_stops_before_reading_datahub(tmp_path, monkeypatch):
    def unreachable():
        raise AssertionError("DataHub ne doit pas être contacté")

    monkeypatch.setattr(cli_module, "from_env", unreachable)

    result = runner.invoke(
        cli_module.app,
        [
            "export-file",
            "--config",
            str(_empty_config(tmp_path)),
            "--output",
            str(tmp_path / "o.ttl"),
        ],
    )

    assert result.exit_code == 2
    assert "Aucune URI de base" in result.output


def test_push_without_base_uri_stops_before_any_network_call(tmp_path):
    result = runner.invoke(
        cli_module.app,
        [
            "push-hdh",
            "--hdh-url",
            "https://hdh.test",
            "--api-key",
            "mdc_x",
            "--config",
            str(_empty_config(tmp_path)),
        ],
    )

    assert result.exit_code == 2
    assert "Aucune URI de base" in result.output


def test_export_uses_the_profile_base_uri(tmp_path, monkeypatch):
    config = tmp_path / "config.yml"
    config.write_text("profiles:\n  prod:\n    base_uri: https://data.exemple.fr\n", "utf-8")
    monkeypatch.setattr(cli_module, "from_env", build_context)
    output = tmp_path / "out.ttl"

    result = runner.invoke(
        cli_module.app,
        ["export-file", "--config", str(config), "--urn", DATAPRODUCT_URN, "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    identifiers = {str(o) for o in Graph().parse(output).objects(None, DCT.identifier)}
    assert any(i.startswith("https://data.exemple.fr/dataset/") for i in identifiers)
    assert URIRef("https://data.exemple.fr/conformsTo/OSIRIS") in set(
        Graph().parse(output).objects(None, DCT.conformsTo)
    )
