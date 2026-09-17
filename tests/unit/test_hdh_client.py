"""emit/hdh_client.py : client HTTP `/ingest/datasets` — statuts de succès,
mapping d'erreurs (401/403/404/autre) et enveloppe des échecs de transport
(story 13). `httpx.get/post/put/delete` sont monkeypatchés directement (pas
de dépendance de test HTTP supplémentaire) — jusqu'ici jamais exercé par la
suite (issue #79)."""

from __future__ import annotations

import httpx
import pytest

from dh_healthdcat.emit.hdh_client import (
    HdhAuthError,
    HdhClient,
    HdhClientError,
    HdhNotFoundError,
    HdhTransportError,
)

CLIENT = HdhClient(base_url="https://hdh.test", api_key="mdc_secret")


def test_whoami_returns_the_json_payload(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, **kw: httpx.Response(200, json={"role": "x"}))

    assert CLIENT.whoami() == {"role": "x"}


def test_create_dataset_posts_turtle_body_and_returns_id(monkeypatch):
    captured = {}

    def fake_post(url, **kw):
        captured["url"] = url
        captured["headers"] = kw["headers"]
        captured["content"] = kw["content"]
        return httpx.Response(200, json={"id": "u1"})

    monkeypatch.setattr(httpx, "post", fake_post)

    assert CLIENT.create_dataset("@prefix : <urn:x> .") == "u1"
    assert captured["url"] == "https://hdh.test/ingest/datasets"
    assert captured["headers"]["X-API-Key"] == "mdc_secret"
    assert captured["headers"]["Content-Type"] == "text/turtle"
    assert captured["content"] == b"@prefix : <urn:x> ."


def test_update_dataset_puts_to_origin_endpoint_with_original_id(monkeypatch):
    captured = {}

    def fake_put(url, **kw):
        captured["url"] = url
        captured["params"] = kw["params"]
        return httpx.Response(200, json={"id": "orig-1"})

    monkeypatch.setattr(httpx, "put", fake_put)

    assert CLIENT.update_dataset("orig-1", "ttl body") == "orig-1"
    assert captured["url"] == "https://hdh.test/ingest/datasets/origin"
    assert captured["params"] == {"originalId": "orig-1"}


def test_delete_dataset_succeeds_without_a_body(monkeypatch):
    monkeypatch.setattr(httpx, "delete", lambda url, **kw: httpx.Response(200))

    CLIENT.delete_dataset("id-1")  # ne lève pas


def test_transport_failure_is_wrapped_before_reaching_the_caller(monkeypatch):
    def raise_connect_error(url, **kw):
        raise httpx.ConnectError("connexion refusée")

    monkeypatch.setattr(httpx, "get", raise_connect_error)

    with pytest.raises(HdhTransportError) as exc_info:
        CLIENT.whoami()
    assert exc_info.value.status_code == 0
    assert "connexion refusée" in exc_info.value.detail


@pytest.mark.parametrize("status", [401, 403])
def test_401_and_403_raise_hdh_auth_error(monkeypatch, status):
    monkeypatch.setattr(
        httpx, "post", lambda url, **kw: httpx.Response(status, json={"detail": "rôle manquant"})
    )

    with pytest.raises(HdhAuthError) as exc_info:
        CLIENT.create_dataset("ttl")
    assert exc_info.value.status_code == status
    assert exc_info.value.detail == "rôle manquant"


def test_404_raises_hdh_not_found_error(monkeypatch):
    monkeypatch.setattr(
        httpx, "put", lambda url, **kw: httpx.Response(404, json={"detail": "jeu inconnu"})
    )

    with pytest.raises(HdhNotFoundError) as exc_info:
        CLIENT.update_dataset("missing-id", "ttl")
    assert exc_info.value.status_code == 404


def test_other_status_raises_generic_hdh_client_error_with_response_text(monkeypatch):
    monkeypatch.setattr(httpx, "delete", lambda url, **kw: httpx.Response(500, text="boom"))

    with pytest.raises(HdhClientError) as exc_info:
        CLIENT.delete_dataset("id-1")
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "boom"


def test_error_body_without_a_detail_key_falls_back_to_the_whole_body(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda url, **kw: httpx.Response(400, json={"error": "oops"})
    )

    with pytest.raises(HdhClientError) as exc_info:
        CLIENT.create_dataset("ttl")
    assert exc_info.value.detail == str({"error": "oops"})
