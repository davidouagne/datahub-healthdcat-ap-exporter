"""Client HTTP pour `/ingest/datasets` du catalogue HDH (Lot 3).

Contrat confirmé par lecture de `api/app/ingest/routes.py` et
`api/app/tests/ingest/test_routes.py` côté
`hdh/catalogue-de-metadonnees/api` :

| Méthode | Chemin                                   | Corps        | 200            |
|---|---|---|---|
| POST    | /ingest/datasets                         | text/turtle  | {"id": uuid}   |
| PUT     | /ingest/datasets/origin?originalId={id}  | text/turtle  | {"id": id}     |
| DELETE  | /ingest/datasets/{id}                    | —            | {"status": "deleted", "id": id} |

Auth : en-tête `X-API-Key`, rôle Keycloak `data-provider` requis. Erreurs :
400 corps vide, 403 rôle absent ou jeu appartenant à un autre fournisseur,
404 jeu non ingéré via cette API (`assert_owner` échoue si aucun
`source_provider` n'est enregistré).

Modèle repris de `api/app/core/parent_connexion.py::ParentCatalogService`,
le client Python déjà utilisé côté HDH pour le même usage (un catalogue
enfant qui pousse vers un catalogue parent) — même en-têtes, même
enchaînement des trois verbes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import httpx


class HdhClientError(Exception):
    """Erreur HTTP côté HDH, avec assez de contexte pour agir sans relire le code."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HDH a répondu {status_code} : {detail}")


class HdhAuthError(HdhClientError):
    """401/403 — clé invalide ou rôle `data-provider` manquant."""


class HdhNotFoundError(HdhClientError):
    """404 — jeu non ingéré via /ingest (PUT/DELETE sur un id inconnu)."""


class HdhTransportError(HdhClientError):
    """Échec de transport (connexion, timeout...) avant toute réponse HTTP —
    distinct d'un statut d'erreur renvoyé par le HDH. Un jeu en échec réseau
    ne doit pas faire échouer les jeux suivants du lot (story 13)."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=0, detail=detail)


class HdhTarget(Protocol):
    """Le seam que `pipeline.push()` traverse : créer ou mettre à jour un
    jeu. Satisfait structurellement par `HdhClient` (production) et par
    `tests/fixtures/fake_hdh.py::InMemoryHdhCatalog` (tests, hors ligne)."""

    def create_dataset(self, turtle: str) -> str: ...

    def update_dataset(self, original_id: str, turtle: str) -> str: ...


@dataclass(frozen=True, slots=True)
class HdhClient:
    base_url: str
    api_key: str
    timeout: float = 60.0

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Content-Type": "text/turtle"}

    @staticmethod
    def _send(request: Callable[[], httpx.Response]) -> httpx.Response:
        """Enveloppe les échecs de transport (connexion, timeout...) avant
        toute réponse HTTP — sans quoi ils échappent à `except HdhClientError`
        côté appelant et avortent tout un lot de poussée (story 13)."""

        try:
            return request()
        except httpx.HTTPError as exc:
            raise HdhTransportError(str(exc)) from exc

    def whoami(self) -> dict:
        """Vérifie la clé avant toute boucle d'envoi (P0-9) — endpoint de
        test documenté côté HDH pour une clé fraîchement générée."""

        response = self._send(
            lambda: httpx.get(
                f"{self.base_url}/api-keys/whoami",
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout,
            )
        )
        self._raise_for_status(response)
        return response.json()

    def create_dataset(self, turtle: str) -> str:
        response = self._send(
            lambda: httpx.post(
                f"{self.base_url}/ingest/datasets",
                headers=self._headers(),
                content=turtle.encode("utf-8"),
                timeout=self.timeout,
            )
        )
        self._raise_for_status(response)
        return response.json()["id"]

    def update_dataset(self, original_id: str, turtle: str) -> str:
        response = self._send(
            lambda: httpx.put(
                f"{self.base_url}/ingest/datasets/origin",
                params={"originalId": original_id},
                headers=self._headers(),
                content=turtle.encode("utf-8"),
                timeout=self.timeout,
            )
        )
        self._raise_for_status(response)
        return response.json()["id"]

    def delete_dataset(self, dataset_id: str) -> None:
        response = self._send(
            lambda: httpx.delete(
                f"{self.base_url}/ingest/datasets/{dataset_id}",
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout,
            )
        )
        self._raise_for_status(response)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        detail = _extract_detail(response)
        if response.status_code in (401, 403):
            raise HdhAuthError(response.status_code, detail)
        if response.status_code == 404:
            raise HdhNotFoundError(response.status_code, detail)
        raise HdhClientError(response.status_code, detail)


def _extract_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("detail", body))
    except ValueError:
        return response.text
