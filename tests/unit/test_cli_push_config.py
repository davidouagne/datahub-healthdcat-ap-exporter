"""Câblage config→CLI de `push-hdh` — spec/spec-feature-catalogue-instance-config.md.

Seuls les chemins d'erreur *antérieurs à tout appel réseau* sont exercés ici :
résolution de configuration (REQ-001/002/004) et absence de clé API
(REQ-006). `--config` est toujours passé explicitement, jamais laissé
implicite (cwd/home) : un `.dh-healthdcat.yml` qui traînerait par accident
dans le répertoire courant ou le home du poste qui exécute la suite ne doit
jamais influencer ces tests (REQ-011)."""

from __future__ import annotations

from typer.testing import CliRunner

from dh_healthdcat.cli import app

runner = CliRunner()


def _write_config(tmp_path, content: str):
    path = tmp_path / "config.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_no_url_anywhere_exits_2(tmp_path):
    config = _write_config(tmp_path, "profiles: {}\n")

    result = runner.invoke(app, ["push-hdh", "--config", str(config)])

    assert result.exit_code == 2


def test_unknown_profile_exits_2_and_lists_known_profiles(tmp_path):
    config = _write_config(
        tmp_path,
        "profiles:\n"
        "  dev:\n    url: https://dev.test\n"
        "  preprod:\n    url: https://preprod.test\n"
        "  prod:\n    url: https://prod.test\n",
    )

    result = runner.invoke(app, ["push-hdh", "--config", str(config), "--profile", "preprd"])

    assert result.exit_code == 2
    assert "dev" in result.output
    assert "preprod" in result.output
    assert "prod" in result.output


def test_missing_config_path_exits_2(tmp_path):
    result = runner.invoke(app, ["push-hdh", "--config", str(tmp_path / "absent.yml")])

    assert result.exit_code == 2


def test_missing_api_key_exits_1(tmp_path):
    config = _write_config(tmp_path, "profiles: {}\n")

    result = runner.invoke(
        app, ["push-hdh", "--hdh-url", "https://exemple.test", "--config", str(config)]
    )

    assert result.exit_code == 1


def test_literal_api_key_in_config_is_rejected_before_any_network_call(tmp_path):
    config = _write_config(
        tmp_path, "profiles:\n  prod:\n    url: https://prod.test\n    api_key: mdc_secret\n"
    )

    result = runner.invoke(app, ["push-hdh", "--config", str(config), "--profile", "prod"])

    assert result.exit_code == 2
    assert "api_key_env" in result.output
