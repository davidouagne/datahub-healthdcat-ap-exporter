"""Définitions canoniques des SP (#134, ADR-0005 §3) : contrat avec ce que
le reader lit réellement, format accepté par `datahub properties upsert`, et
commande `dh-healthdcat properties`."""

from __future__ import annotations

import functools
from pathlib import Path

import pytest
import yaml
from datahub.api.entities.structuredproperties.structuredproperties import StructuredProperties
from typer.testing import CliRunner

import dh_healthdcat.cli as cli_module
from dh_healthdcat import sp, sp_definitions
from dh_healthdcat.mapping import vocabularies
from dh_healthdcat.reader import props
from dh_healthdcat.reader.dataproduct import read_data_product
from dh_healthdcat.reader.graph import _entity_type
from tests.fixtures.fake_datahub import BASE_URI, DATAPRODUCT_URN, build_context

# Getter du reader → (types DataHub compatibles, cardinalité attendue).
GETTERS = {
    "get_string": ({"string", "rich_text"}, "SINGLE"),
    "get_strings": ({"string", "rich_text"}, "MULTIPLE"),
    "get_int": ({"number"}, "SINGLE"),
    "get_ints": ({"number"}, "MULTIPLE"),
    "get_date": ({"date"}, "SINGLE"),
    "get_dates": ({"date"}, "MULTIPLE"),
    "get_bool": ({"string"}, "SINGLE"),
}
# Position du paramètre `dataset_urn` (l'entité lue) : get_string(s) prennent
# `ctx` en plus.
_URN_INDEX = {name: 4 if name in ("get_string", "get_strings") else 3 for name in GETTERS}


@pytest.fixture(scope="module")
def reads() -> dict[str, set[tuple[str, str]]]:
    """SP lues pendant la lecture complète du DataProduct de la fixture :
    nom local → {(getter, type d'entité)}. Seul l'appel le plus externe compte
    (`get_string` délègue à `get_strings`)."""

    recorded: dict[str, set[tuple[str, str]]] = {}
    depth = 0
    originals = {name: getattr(props, name) for name in GETTERS}

    def spy(getter_name, original):
        @functools.wraps(original)
        def wrapper(*args, **kwargs):
            nonlocal depth
            if depth == 0:
                name = args[2] if getter_name in ("get_string", "get_strings") else args[1]
                urn = args[_URN_INDEX[getter_name]]
                recorded.setdefault(name, set()).add((getter_name, _entity_type(urn)))
            depth += 1
            try:
                return original(*args, **kwargs)
            finally:
                depth -= 1

        return wrapper

    with pytest.MonkeyPatch.context() as mp:
        for name, original in originals.items():
            mp.setattr(props, name, spy(name, original))
        read_data_product(build_context(), DATAPRODUCT_URN, base_uri=BASE_URI)
    return recorded


def _by_name() -> dict[str, sp_definitions.Definition]:
    return {d.name: d for d in sp_definitions.definitions()}


class TestContract:
    def test_every_read_property_has_a_definition_and_vice_versa(self, reads):
        assert set(reads) == set(_by_name())

    def test_type_and_cardinality_match_the_getter(self, reads):
        mismatches = []
        for name, calls in reads.items():
            definition = _by_name()[name]
            for getter, _ in calls:
                types, cardinality = GETTERS[getter]
                if definition.type not in types or definition.cardinality != cardinality:
                    mismatches.append((name, getter, definition.type, definition.cardinality))
        assert mismatches == []

    def test_entity_types_cover_the_entities_read(self, reads):
        missing = [
            (name, entity_type)
            for name, calls in reads.items()
            for _, entity_type in calls
            if entity_type not in _by_name()[name].entity_types
        ]
        assert missing == []

    def test_booleans_use_the_boolean_vocabulary(self, reads):
        booleans = [n for n, calls in reads.items() if any(g == "get_bool" for g, _ in calls)]
        assert booleans
        assert all(_by_name()[n].vocabulary == "Booleans" for n in booleans)


def test_definitions_file_holds_local_names_only():
    """Le préfixe n'est déclaré que dans sp.py : `write()` l'ajoute."""

    assert sp.SP_PREFIX not in sp_definitions.DEFINITIONS_FILE.read_text(encoding="utf-8")


class TestUpsertFormat:
    def test_written_file_is_accepted_by_datahub_properties_upsert(self, tmp_path):
        """`datahub properties upsert -f` = `from_yaml` puis `generate_mcps` ;
        seule l'émission vers le serveur manque ici."""

        path = sp_definitions.write(tmp_path / "sp.yml")

        parsed = StructuredProperties.from_yaml(str(path))
        assert len(parsed) == len(sp_definitions.definitions())
        assert all(p.generate_mcps() for p in parsed)
        assert {p.fqn for p in parsed} == {
            sp.qualified(d.name) for d in sp_definitions.definitions()
        }

    def test_allowed_values_are_exactly_the_vocabulary_codes(self, tmp_path):
        entries = {
            e["id"]: e for e in yaml.safe_load(sp_definitions.write(tmp_path).read_text("utf-8"))
        }

        for definition in sp_definitions.definitions():
            entry = entries[sp.qualified(definition.name)]
            if definition.vocabulary is None:
                assert "allowed_values" not in entry, definition.name
                continue
            vocabulary = vocabularies.load(definition.vocabulary)
            assert [v["value"] for v in entry["allowed_values"]] == list(vocabulary.code_to_uri)

    def test_reference_specification_is_not_restricted(self):
        """Le reader accepte tout code grâce au repli dct:conformsTo local."""

        assert _by_name()["referenceSpecification"].vocabulary is None


def test_cli_writes_into_a_directory(tmp_path):
    result = CliRunner().invoke(cli_module.app, ["properties", "--output", str(tmp_path)])

    assert result.exit_code == 0, result.output
    written = tmp_path / sp_definitions.DEFAULT_FILE_NAME
    assert written.is_file()
    assert f"{len(sp_definitions.definitions())} définitions écrites" in result.output
    assert "datahub properties upsert -f" in result.output


class TestMigrationGuide:
    """Guide 0.3.0 (#140) : la table de correspondance est vérifiée contre les
    définitions canoniques, et l'erreur de l'ancien préfixe y renvoie."""

    GUIDE = Path(__file__).parents[2] / "docs" / "migration-0.3.0.md"

    def test_error_message_points_to_the_guide(self):
        assert self.GUIDE.is_file()
        assert sp.MIGRATION_GUIDE.endswith("/blob/main/docs/migration-0.3.0.md")

    def test_correspondence_table_matches_the_definitions(self):
        rows = [
            [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
            for line in self.GUIDE.read_text(encoding="utf-8").splitlines()
            if line.startswith(f"| `{sp.LEGACY_PREFIX}")
        ]
        expected = [
            [
                sp.LEGACY_PREFIX + d.name,
                sp.qualified(d.name),
                d.type,
                d.cardinality,
                ", ".join(d.entity_types),
            ]
            for d in sp_definitions.definitions()
        ]
        assert rows == expected
