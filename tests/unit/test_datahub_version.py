"""Contrôle de la version du serveur DataHub au démarrage (#128, ADR-0004 §5) :
lecture de `/config` à la frontière `ReadContext`, décision dans
`datahub_version`, et comportement des deux commandes (avertir, ou échouer
avec `--strict-version`). Le serveur est le double de test, sans réseau."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from typer.testing import CliRunner

import dh_healthdcat.cli as cli_module
from dh_healthdcat import datahub_version
from dh_healthdcat.emit.hdh_client import HdhClient
from dh_healthdcat.reader.graph import ServerInfo
from tests.fixtures.fake_datahub import DATAPRODUCT_URN, build_context

RANGE = SpecifierSet(">=1.7,<1.8")
runner = CliRunner()


class TestSupportedRange:
    def test_is_read_from_the_installed_package_and_matches_pyproject(self):
        """Source unique (ADR-0004 §2) : la plage relue des métadonnées est
        exactement la contrainte acryl-datahub de pyproject.toml."""

        pyproject = Path(__file__).parents[2] / "pyproject.toml"
        dependencies = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"][
            "dependencies"
        ]
        [declared] = [
            Requirement(d).specifier for d in dependencies if Requirement(d).name == "acryl-datahub"
        ]
        assert datahub_version.supported_range() == declared


class TestCheck:
    @pytest.mark.parametrize("version", ["v1.7.0", "v1.7.0.1", "1.7.0.18", "v1.7.0.1-SNAPSHOT"])
    def test_in_range_says_nothing(self, version):
        assert datahub_version.check(ServerInfo(version=version), RANGE) is None

    @pytest.mark.parametrize("version", ["v1.8.0", "v1.6.0.3", "v1.8.0rc2"])
    def test_out_of_range_names_version_and_range(self, version):
        message = datahub_version.check(ServerInfo(version=version), RANGE)

        assert message is not None
        assert version in message
        assert "hors de la plage supportée (<1.8,>=1.7)" in message

    @pytest.mark.parametrize(
        ("server", "reason"),
        [
            (ServerInfo(version=None), "absente de /config"),
            (ServerInfo(version=None, unreachable=True), "/config inaccessible"),
            (ServerInfo(version="v1.7.0.1", is_cloud=True), "DataHub Cloud"),
            (ServerInfo(version="head"), "« head » illisible"),
        ],
    )
    def test_unrecognized_cases(self, server, reason):
        message = datahub_version.check(server, RANGE)

        assert message is not None
        assert "non reconnue" in message
        assert reason in message


class TestServerInfo:
    def test_reads_version_from_config(self):
        assert build_context().server_info() == ServerInfo(version="v1.7.0.1")

    def test_cloud_is_any_non_core_server_env(self):
        ctx = build_context()
        ctx.graph.config = {
            "versions": {"acryldata/datahub": {"version": "v0.3.12"}},
            "datahub": {"serverEnv": "cloud"},
        }

        assert ctx.server_info().is_cloud is True

    def test_missing_version(self):
        ctx = build_context()
        ctx.graph.config = {"datahub": {"serverEnv": "core"}}

        assert ctx.server_info() == ServerInfo(version=None)

    def test_unreachable_config_does_not_raise(self):
        ctx = build_context()
        ctx.graph.config = ConnectionError("refused")

        assert ctx.server_info() == ServerInfo(version=None, unreachable=True)


def _context_with_version(version: str):
    def factory():
        ctx = build_context()
        ctx.graph.config = {"versions": {"acryldata/datahub": {"version": version}}}
        return ctx

    return factory


class TestCli:
    def _export(self, tmp_path, *extra):
        output = str(tmp_path / "out.ttl")
        args = ["export-file", "--output", output, "--urn", DATAPRODUCT_URN, *extra]
        return runner.invoke(cli_module.app, args)

    def test_in_range_prints_no_version_message(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli_module, "from_env", build_context)

        result = self._export(tmp_path)

        assert result.exit_code == 0, result.output
        assert "Serveur DataHub" not in result.output
        assert "non reconnue" not in result.output

    def test_out_of_range_warns_and_exports(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli_module, "from_env", _context_with_version("v1.8.0"))

        result = self._export(tmp_path)

        assert result.exit_code == 0, result.output
        assert "Serveur DataHub v1.8.0 hors de la plage supportée" in result.output
        assert (tmp_path / "out.ttl").is_file()

    def test_unrecognized_warns_and_exports(self, tmp_path, monkeypatch):
        def unreachable():
            ctx = build_context()
            ctx.graph.config = ConnectionError("refused")
            return ctx

        monkeypatch.setattr(cli_module, "from_env", unreachable)

        result = self._export(tmp_path)

        assert result.exit_code == 0, result.output
        assert "non reconnue (/config inaccessible)" in result.output

    def test_strict_version_fails_before_any_selection(self, tmp_path, monkeypatch):
        contexts = []

        def factory():
            ctx = _context_with_version("v1.8.0")()
            contexts.append(ctx)
            return ctx

        monkeypatch.setattr(cli_module, "from_env", factory)

        result = self._export(tmp_path, "--strict-version")

        assert result.exit_code == 1
        assert "(--strict-version)" in result.output
        assert not (tmp_path / "out.ttl").exists()
        assert contexts[0].graph.last_extra_or_filters is None
        assert contexts[0].graph.get_entity_semityped_calls == []

    def test_strict_version_in_range_exports(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli_module, "from_env", build_context)

        result = self._export(tmp_path, "--strict-version")

        assert result.exit_code == 0, result.output

    def test_push_hdh_strict_version_fails_before_any_push(self, tmp_path, monkeypatch):
        config = tmp_path / "config.yml"
        config.write_text("profiles: {}\n", encoding="utf-8")
        monkeypatch.setattr(cli_module, "from_env", _context_with_version("v1.6.0.3"))
        monkeypatch.setattr(HdhClient, "whoami", lambda self: {"role": "data-provider"})
        created = []
        monkeypatch.setattr(
            HdhClient, "create_dataset", lambda self, turtle: created.append(turtle) or "x"
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
                "--strict-version",
            ],
        )

        assert result.exit_code == 1
        assert "v1.6.0.3 hors de la plage supportée" in result.output
        assert created == []
