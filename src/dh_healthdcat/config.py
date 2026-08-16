"""Résolution de l'instance du Catalogue de métadonnées —
spec/spec-feature-catalogue-instance-config.md.

Sépare strictement l'I/O (`find_config_file`, `load_config`) de la décision
(`resolve_target`) : c'est ce qui rend la précédence
`--hdh-url` > `$HDH_URL` > profil testable sans réseau, sans fichier, sans
`monkeypatch` sur `os.environ` (REQ-007) — même contrainte que le reste du
dépôt (CONTRIBUTING.md:24-28). `resolve_target` reçoit `config` et `env` déjà
construits ; c'est `cli.py` qui fait le pont vers le système de fichiers et
`os.environ` réels."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

import yaml

DEFAULT_API_KEY_ENV = "HDH_API_KEY"
CONFIG_FILENAME = ".dh-healthdcat.yml"

_DEFAULT_PORTS = {"http": 80, "https": 443}


class ConfigError(Exception):
    """Erreur de configuration : le message porte le profil et/ou le fichier
    concernés, pour agir sans relire le code. Jamais un repli silencieux
    (REQ-004) — une `ConfigError` non attrapée doit interrompre le traitement
    avant tout appel réseau."""


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    url: str | None = None
    api_key_env: str | None = None


@dataclass(frozen=True, slots=True)
class Config:
    path: Path | None
    profiles: dict[str, Profile] = field(default_factory=dict)
    default_profile: str | None = None


@dataclass(frozen=True, slots=True)
class Resolved:
    url: str
    api_key_env: str
    profile_name: str | None


def normalize_url(raw: str) -> str:
    """Unique normalisation d'URL du dépôt (REQ-010) : alimente à la fois
    `HdhClient(base_url=...)` et la clé de compartiment de `PushState`, pour
    qu'ils ne puissent jamais diverger."""

    parts = urlsplit(raw.strip())
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    port = parts.port
    if port is not None and _DEFAULT_PORTS.get(scheme) == port:
        port = None
    netloc = hostname if port is None else f"{hostname}:{port}"
    path = parts.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def find_config_file(*, explicit: Path | None, env: Mapping[str, str], cwd: Path, home: Path) -> Path | None:
    """Résout le chemin du fichier de configuration : `--config` (explicite)
    > `$HDH_CONFIG` > `<cwd>/.dh-healthdcat.yml` > `<home>/.dh-healthdcat.yml`
    — premier trouvé gagne, sans fusion (REQ-002).

    Un chemin explicite (option ou variable) introuvable est une erreur ;
    l'absence des deux chemins implicites ne l'est pas (renvoie None : aucune
    configuration ne s'applique)."""

    if explicit is not None:
        if not explicit.is_file():
            raise ConfigError(f"Fichier de configuration introuvable : {explicit}")
        return explicit

    env_path = env.get("HDH_CONFIG")
    if env_path:
        path = Path(env_path)
        if not path.is_file():
            raise ConfigError(f"Fichier de configuration introuvable (HDH_CONFIG) : {path}")
        return path

    cwd_path = cwd / CONFIG_FILENAME
    if cwd_path.is_file():
        return cwd_path

    home_path = home / CONFIG_FILENAME
    if home_path.is_file():
        return home_path

    return None


def load_config(path: Path) -> Config:
    """Charge et valide le fichier YAML de configuration. Avec
    `resolve_target`, seule fonction du module à faire de l'I/O."""

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Fichier de configuration invalide ({path}) : {exc}") from exc

    raw = raw or {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Fichier de configuration invalide ({path}) : attendu un mapping en racine")

    raw_profiles = raw.get("profiles") or {}
    if not isinstance(raw_profiles, dict):
        raise ConfigError(f"Fichier de configuration invalide ({path}) : `profiles` doit être un mapping")

    profiles: dict[str, Profile] = {}
    for name, body in raw_profiles.items():
        body = body or {}
        if not isinstance(body, dict):
            raise ConfigError(f"Profil {name!r} invalide ({path}) : attendu un mapping")
        if "api_key" in body:
            raise ConfigError(
                f"Profil {name!r} ({path}) : `api_key` en clair n'est pas autorisé dans un fichier "
                "de configuration versionnable — déclarez `api_key_env` (nom de variable "
                "d'environnement) à la place."
            )
        url = body.get("url")
        api_key_env = body.get("api_key_env")
        if url is not None and not isinstance(url, str):
            raise ConfigError(f"Profil {name!r} ({path}) : `url` doit être une chaîne (reçu {url!r}).")
        if api_key_env is not None and not isinstance(api_key_env, str):
            raise ConfigError(f"Profil {name!r} ({path}) : `api_key_env` doit être une chaîne (reçu {api_key_env!r}).")
        profiles[name] = Profile(name=name, url=url, api_key_env=api_key_env)

    default_profile = raw.get("default_profile")
    if default_profile is not None and default_profile not in profiles:
        known = ", ".join(sorted(profiles)) or "aucun"
        raise ConfigError(f"`default_profile: {default_profile}` ({path}) ne correspond à aucun profil déclaré ({known}).")

    return Config(path=path, profiles=profiles, default_profile=default_profile)


def resolve_target(
    *,
    config: Config | None,
    env: Mapping[str, str],
    cli_url: str | None,
    cli_profile: str | None,
    cli_api_key_env: str | None,
) -> Resolved:
    """Résolution champ par champ (REQ-005), pas source par source : l'URL et
    la variable de clé se résolvent indépendamment. Fonction pure (REQ-007) :
    ni I/O ni accès à `os.environ` — `config` et `env` sont injectés."""

    config = config or Config(path=None)

    profile_name = cli_profile or env.get("HDH_PROFILE") or config.default_profile
    if profile_name is None and len(config.profiles) == 1:
        (profile_name,) = config.profiles

    profile: Profile | None = None
    if profile_name is not None:
        profile = config.profiles.get(profile_name)
        if profile is None:
            known = ", ".join(sorted(config.profiles)) or "aucun"
            location = f" ({config.path})" if config.path else ""
            raise ConfigError(f"Profil {profile_name!r} inconnu{location} — profils déclarés : {known}.")

    raw_url = cli_url or env.get("HDH_URL") or (profile.url if profile else None)
    if not raw_url:
        raise ConfigError(
            "Aucune URL de catalogue : passez --hdh-url, définissez $HDH_URL, ou déclarez `url` "
            "dans le profil sélectionné."
        )

    api_key_env = cli_api_key_env or (profile.api_key_env if profile else None) or DEFAULT_API_KEY_ENV

    return Resolved(url=normalize_url(raw_url), api_key_env=api_key_env, profile_name=profile_name)
