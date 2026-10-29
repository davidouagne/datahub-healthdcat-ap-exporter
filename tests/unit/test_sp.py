from pathlib import Path

from typer.testing import CliRunner

import dh_healthdcat
import dh_healthdcat.cli as cli_module
from dh_healthdcat import sp
from dh_healthdcat.reader.graph import PropertyDefinition
from tests.fixtures.fake_datahub import DATAPRODUCT_URN, build_context

SRC = Path(dh_healthdcat.__file__).parent


def test_qualified_prefixes_local_name() -> None:
    assert sp.qualified("healthTheme") == sp.SP_PREFIX + "healthTheme"


def test_prefix_is_declared_only_in_sp_module() -> None:
    offenders = [
        path.relative_to(SRC).as_posix()
        for path in SRC.rglob("*.py")
        if path.name != "sp.py" and sp.SP_PREFIX in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


class TestLegacyPrefix:
    """Coupure nette (ADR-0005 §2) : l'ancien préfixe n'est jamais lu, il ne
    sert qu'à arrêter l'export d'une instance non migrée."""

    def test_legacy_only_instance_gets_one_error_with_the_guide(self) -> None:
        message = sp.legacy_prefix_error(
            [sp.LEGACY_PREFIX + "healthTheme", sp.LEGACY_PREFIX + "license", "other.x"]
        )

        assert message is not None
        assert "2 structured properties fr.aphp.healthdcat.*" in message
        assert sp.MIGRATION_GUIDE in message

    def test_migrated_instance_passes_even_with_leftovers(self) -> None:
        assert (
            sp.legacy_prefix_error([sp.qualified("healthTheme"), sp.LEGACY_PREFIX + "healthTheme"])
            is None
        )

    def test_instance_without_any_property_passes(self) -> None:
        assert sp.legacy_prefix_error(["other.x"]) is None


def _context_with_definitions(*names: str):
    def factory():
        ctx = build_context()
        ctx._property_definitions = {
            name: PropertyDefinition(
                qualified_name=name,
                urn=f"urn:li:structuredProperty:{name}",
                value_type="urn:li:dataType:datahub.string",
                cardinality="SINGLE",
            )
            for name in names
        }
        return ctx

    return factory


class TestCli:
    def _export(self, tmp_path):
        output = str(tmp_path / "out.ttl")
        return CliRunner().invoke(
            cli_module.app, ["export-file", "--output", output, "--urn", DATAPRODUCT_URN]
        )

    def test_legacy_only_instance_stops_before_any_selection(self, tmp_path, monkeypatch):
        contexts = []

        def factory():
            ctx = _context_with_definitions(sp.LEGACY_PREFIX + "healthTheme")()
            contexts.append(ctx)
            return ctx

        monkeypatch.setattr(cli_module, "from_env", factory)

        result = self._export(tmp_path)

        assert result.exit_code == 1
        assert result.output.count(sp.MIGRATION_GUIDE) == 1
        assert not (tmp_path / "out.ttl").exists()
        assert contexts[0].graph.get_entity_semityped_calls == []

    def test_instance_with_both_prefixes_exports(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            cli_module,
            "from_env",
            _context_with_definitions(
                sp.qualified("healthTheme"), sp.LEGACY_PREFIX + "healthTheme"
            ),
        )

        result = self._export(tmp_path)

        assert sp.MIGRATION_GUIDE not in result.output
        assert (tmp_path / "out.ttl").is_file()
