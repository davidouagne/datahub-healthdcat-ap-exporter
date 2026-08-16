"""Résolution de l'instance du Catalogue de métadonnées (config.py) —
spec/spec-feature-catalogue-instance-config.md.

Trois couches testées séparément, comme selection.py sépare filtre pur et
appel réseau :

1. `normalize_url` — fonction pure, l'unique normalisation du dépôt (REQ-010).
2. `find_config_file`/`load_config` — I/O sur `tmp_path`, jamais sur le
   répertoire courant ou le home réels du poste qui exécute la suite.
3. `resolve_target` — fonction pure (REQ-007) : `env` est toujours injecté en
   dict, jamais lu depuis `os.environ` réel, donc aucun `monkeypatch` requis
   nulle part dans ce fichier."""

from __future__ import annotations

import pytest

from dh_healthdcat.config import (
    DEFAULT_API_KEY_ENV,
    Config,
    ConfigError,
    Profile,
    find_config_file,
    load_config,
    normalize_url,
    resolve_target,
)


class TestNormalizeUrl:
    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTPS://Exemple.FR") == "https://exemple.fr"

    def test_strips_default_https_port(self):
        assert normalize_url("https://Exemple.fr:443/api/") == "https://exemple.fr/api"

    def test_strips_default_http_port(self):
        assert normalize_url("http://exemple.fr:80") == "http://exemple.fr"

    def test_keeps_non_default_port(self):
        assert normalize_url("https://exemple.fr:8443") == "https://exemple.fr:8443"

    def test_strips_trailing_slash_without_path(self):
        assert normalize_url("https://exemple.fr/") == "https://exemple.fr"

    def test_strips_multiple_trailing_slashes(self):
        assert normalize_url("https://exemple.fr/api//") == "https://exemple.fr/api"


class TestFindConfigFile:
    def test_explicit_path_used_when_present(self, tmp_path):
        explicit = tmp_path / "custom.yml"
        explicit.write_text("profiles: {}\n", encoding="utf-8")

        found = find_config_file(explicit=explicit, env={}, cwd=tmp_path / "cwd", home=tmp_path / "home")

        assert found == explicit

    def test_explicit_path_missing_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="introuvable"):
            find_config_file(explicit=tmp_path / "absent.yml", env={}, cwd=tmp_path, home=tmp_path)

    def test_explicit_path_pointing_at_a_directory_raises(self, tmp_path):
        directory = tmp_path / "not-a-file"
        directory.mkdir()

        with pytest.raises(ConfigError, match="introuvable"):
            find_config_file(explicit=directory, env={}, cwd=tmp_path, home=tmp_path)

    def test_env_path_used_when_present(self, tmp_path):
        env_path = tmp_path / "from-env.yml"
        env_path.write_text("profiles: {}\n", encoding="utf-8")

        found = find_config_file(explicit=None, env={"HDH_CONFIG": str(env_path)}, cwd=tmp_path, home=tmp_path)

        assert found == env_path

    def test_env_path_missing_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="HDH_CONFIG"):
            find_config_file(explicit=None, env={"HDH_CONFIG": str(tmp_path / "absent.yml")}, cwd=tmp_path, home=tmp_path)

    def test_cwd_wins_over_home_no_merge(self, tmp_path):
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()
        (cwd / ".dh-healthdcat.yml").write_text("profiles: {}\n", encoding="utf-8")
        (home / ".dh-healthdcat.yml").write_text("profiles: {}\n", encoding="utf-8")

        found = find_config_file(explicit=None, env={}, cwd=cwd, home=home)

        assert found == cwd / ".dh-healthdcat.yml"

    def test_home_used_when_cwd_absent(self, tmp_path):
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()
        (home / ".dh-healthdcat.yml").write_text("profiles: {}\n", encoding="utf-8")

        found = find_config_file(explicit=None, env={}, cwd=cwd, home=home)

        assert found == home / ".dh-healthdcat.yml"

    def test_returns_none_when_neither_exists(self, tmp_path):
        cwd = tmp_path / "cwd"
        home = tmp_path / "home"
        cwd.mkdir()
        home.mkdir()

        assert find_config_file(explicit=None, env={}, cwd=cwd, home=home) is None


class TestLoadConfig:
    def test_loads_profiles_and_default(self, tmp_path):
        path = tmp_path / "config.yml"
        path.write_text(
            "default_profile: dev\n"
            "profiles:\n"
            "  dev:\n"
            "    url: https://dev.test\n"
            "    api_key_env: DEV_KEY\n"
            "  prod:\n"
            "    url: https://prod.test\n",
            encoding="utf-8",
        )

        config = load_config(path)

        assert config.path == path
        assert config.default_profile == "dev"
        assert config.profiles["dev"] == Profile(name="dev", url="https://dev.test", api_key_env="DEV_KEY")
        assert config.profiles["prod"] == Profile(name="prod", url="https://prod.test", api_key_env=None)

    def test_empty_file_yields_no_profiles(self, tmp_path):
        path = tmp_path / "config.yml"
        path.write_text("", encoding="utf-8")

        config = load_config(path)

        assert config.profiles == {}
        assert config.default_profile is None

    def test_rejects_literal_api_key(self, tmp_path):
        path = tmp_path / "config.yml"
        path.write_text("profiles:\n  prod:\n    url: https://prod.test\n    api_key: mdc_secret\n", encoding="utf-8")

        with pytest.raises(ConfigError, match="prod") as excinfo:
            load_config(path)

        assert "api_key_env" in str(excinfo.value)
        assert str(path) in str(excinfo.value)

    def test_rejects_unknown_default_profile(self, tmp_path):
        path = tmp_path / "config.yml"
        path.write_text("default_profile: preprod\nprofiles:\n  dev:\n    url: https://dev.test\n", encoding="utf-8")

        with pytest.raises(ConfigError, match="preprod"):
            load_config(path)

    def test_malformed_yaml_raises(self, tmp_path):
        path = tmp_path / "config.yml"
        path.write_text("profiles: [this is not a mapping\n", encoding="utf-8")

        with pytest.raises(ConfigError):
            load_config(path)

    def test_rejects_non_string_url(self, tmp_path):
        """Un `url:` non quoté que YAML interprète comme un nombre (ex. un
        port oublié) doit être une erreur explicite, pas un crash de
        `normalize_url` en aval."""

        path = tmp_path / "config.yml"
        path.write_text("profiles:\n  prod:\n    url: 8443\n", encoding="utf-8")

        with pytest.raises(ConfigError, match="prod"):
            load_config(path)

    def test_rejects_non_string_api_key_env(self, tmp_path):
        path = tmp_path / "config.yml"
        path.write_text("profiles:\n  prod:\n    url: https://prod.test\n    api_key_env: 123\n", encoding="utf-8")

        with pytest.raises(ConfigError, match="prod"):
            load_config(path)


class TestResolveTarget:
    def test_cli_url_wins_over_env_and_profile(self):
        config = Config(path=None, profiles={"prod": Profile(name="prod", url="https://profile.test")})

        resolved = resolve_target(
            config=config, env={"HDH_URL": "https://env.test"}, cli_url="https://cli.test", cli_profile="prod", cli_api_key_env=None
        )

        assert resolved.url == "https://cli.test"

    def test_env_url_wins_over_profile(self):
        config = Config(path=None, profiles={"prod": Profile(name="prod", url="https://profile.test")})

        resolved = resolve_target(
            config=config, env={"HDH_URL": "https://env.test"}, cli_url=None, cli_profile="prod", cli_api_key_env=None
        )

        assert resolved.url == "https://env.test"

    def test_profile_url_used_when_no_override(self):
        config = Config(path=None, profiles={"prod": Profile(name="prod", url="https://profile.test")})

        resolved = resolve_target(config=config, env={}, cli_url=None, cli_profile="prod", cli_api_key_env=None)

        assert resolved.url == "https://profile.test"
        assert resolved.profile_name == "prod"

    def test_url_is_normalized(self):
        config = Config(path=None, profiles={"prod": Profile(name="prod", url="https://Profile.test:443/")})

        resolved = resolve_target(config=config, env={}, cli_url=None, cli_profile="prod", cli_api_key_env=None)

        assert resolved.url == "https://profile.test"

    def test_no_url_anywhere_raises(self):
        with pytest.raises(ConfigError, match="URL"):
            resolve_target(config=None, env={}, cli_url=None, cli_profile=None, cli_api_key_env=None)

    def test_unknown_profile_raises_listing_known_profiles(self):
        config = Config(path=None, profiles={"dev": Profile(name="dev", url="https://dev.test"), "prod": Profile(name="prod", url="https://prod.test")})

        with pytest.raises(ConfigError, match="dev") as excinfo:
            resolve_target(config=config, env={}, cli_url=None, cli_profile="preprd", cli_api_key_env=None)

        assert "prod" in str(excinfo.value)

    def test_unknown_profile_raises_even_when_cli_url_given(self):
        """REQ-004 : un nom de profil inconnu est toujours une erreur, jamais
        un repli — même si l'URL est par ailleurs disponible autrement."""

        config = Config(path=None, profiles={"dev": Profile(name="dev", url="https://dev.test")})

        with pytest.raises(ConfigError, match="preprd"):
            resolve_target(config=config, env={}, cli_url="https://cli.test", cli_profile="preprd", cli_api_key_env=None)

    def test_sole_profile_used_when_no_selection(self):
        config = Config(path=None, profiles={"only": Profile(name="only", url="https://only.test")})

        resolved = resolve_target(config=config, env={}, cli_url=None, cli_profile=None, cli_api_key_env=None)

        assert resolved.profile_name == "only"
        assert resolved.url == "https://only.test"

    def test_no_profile_selected_when_several_exist_and_url_given(self):
        config = Config(path=None, profiles={"dev": Profile(name="dev", url="https://dev.test"), "prod": Profile(name="prod", url="https://prod.test")})

        resolved = resolve_target(config=config, env={}, cli_url="https://cli.test", cli_profile=None, cli_api_key_env=None)

        assert resolved.profile_name is None
        assert resolved.url == "https://cli.test"

    def test_default_profile_used_over_sole_profile_rule(self):
        config = Config(
            path=None,
            profiles={"dev": Profile(name="dev", url="https://dev.test"), "prod": Profile(name="prod", url="https://prod.test")},
            default_profile="prod",
        )

        resolved = resolve_target(config=config, env={}, cli_url=None, cli_profile=None, cli_api_key_env=None)

        assert resolved.profile_name == "prod"

    def test_cli_profile_wins_over_env_profile_and_default(self):
        config = Config(
            path=None,
            profiles={"dev": Profile(name="dev", url="https://dev.test"), "prod": Profile(name="prod", url="https://prod.test")},
            default_profile="prod",
        )

        resolved = resolve_target(config=config, env={"HDH_PROFILE": "prod"}, cli_url=None, cli_profile="dev", cli_api_key_env=None)

        assert resolved.profile_name == "dev"

    def test_cli_api_key_env_wins_over_profile_and_default(self):
        config = Config(path=None, profiles={"prod": Profile(name="prod", url="https://prod.test", api_key_env="PROFILE_KEY")})

        resolved = resolve_target(config=config, env={}, cli_url=None, cli_profile="prod", cli_api_key_env="CLI_KEY")

        assert resolved.api_key_env == "CLI_KEY"

    def test_profile_api_key_env_used_when_no_cli_override(self):
        config = Config(path=None, profiles={"prod": Profile(name="prod", url="https://prod.test", api_key_env="PROFILE_KEY")})

        resolved = resolve_target(config=config, env={}, cli_url=None, cli_profile="prod", cli_api_key_env=None)

        assert resolved.api_key_env == "PROFILE_KEY"

    def test_default_api_key_env_when_nothing_declared(self):
        resolved = resolve_target(config=None, env={}, cli_url="https://cli.test", cli_profile=None, cli_api_key_env=None)

        assert resolved.api_key_env == DEFAULT_API_KEY_ENV

    def test_resolution_is_field_by_field_not_source_by_source(self):
        """REQ-005 : --profile prod --api-key-env K prend l'URL du profil et
        la variable de clé donnée en ligne de commande, jamais l'un ou
        l'autre en bloc."""

        config = Config(path=None, profiles={"prod": Profile(name="prod", url="https://prod.test", api_key_env="PROFILE_KEY")})

        resolved = resolve_target(config=config, env={}, cli_url=None, cli_profile="prod", cli_api_key_env="CLI_KEY")

        assert resolved.url == "https://prod.test"
        assert resolved.api_key_env == "CLI_KEY"
