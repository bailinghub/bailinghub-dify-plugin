from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import pytest

from tools._client import (
    MAX_RESPONSE_BYTES,
    BailingHubClient,
    BailingHubClientError,
    normalize_base_url,
)

JOB_ID = "11111111-1111-4111-8111-111111111111"


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, *, raw: bytes | None = None):
        self.status_code = status_code
        self.raw = raw if raw is not None else json.dumps(payload or {}).encode()
        self.closed = False

    def iter_content(self, chunk_size: int) -> Iterable[bytes]:
        del chunk_size
        yield self.raw

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, *responses: FakeResponse):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


def client(*responses: FakeResponse) -> tuple[BailingHubClient, FakeSession]:
    session = FakeSession(*responses)
    return BailingHubClient("https://hub.example.com", "secret-token", session=session), session


def test_normalize_base_url_requires_https_except_loopback() -> None:
    assert normalize_base_url("https://hub.example.com/base/") == "https://hub.example.com/base"
    assert normalize_base_url("http://127.0.0.1:3000/") == "http://127.0.0.1:3000"
    with pytest.raises(ValueError, match="Use HTTPS"):
        normalize_base_url("http://hub.example.com")
    with pytest.raises(ValueError, match="embedded credentials"):
        normalize_base_url("https://admin:secret@hub.example.com")


def test_submit_job_uses_only_public_contract_and_filters_response() -> None:
    api, session = client(
        FakeResponse(
            202,
            {
                "job_id": JOB_ID,
                "request_id": "dify:run:step",
                "status": "queued",
                "route": "orders",
                "project": "must-not-leak",
                "profile": "must-not-leak",
                "metadata": {"must": "not leak"},
            },
        )
    )

    result = api.submit_job(request_id="dify:run:step", route="orders", input_text="Read order 42")

    assert result == {
        "job_id": JOB_ID,
        "request_id": "dify:run:step",
        "status": "queued",
        "terminal": False,
        "route": "orders",
    }
    call = session.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://hub.example.com/run"
    assert call["headers"]["Authorization"] == "Bearer secret-token"
    assert call["json"] == {
        "request_id": "dify:run:step",
        "route": "orders",
        "input": "Read order 42",
    }


def test_validate_credentials_checks_health_and_authenticated_job_surface() -> None:
    api, session = client(FakeResponse(200, {"status": "ok"}), FakeResponse(404, {}))
    api.validate_credentials()
    assert session.calls[0]["url"].endswith("/health")
    assert "Authorization" not in session.calls[0]["headers"]
    assert session.calls[1]["url"].endswith("/jobs/00000000-0000-0000-0000-000000000000")
    assert session.calls[1]["headers"]["Authorization"] == "Bearer secret-token"


def test_upstream_error_does_not_expose_arbitrary_body_or_token() -> None:
    api, _ = client(FakeResponse(401, raw=b"secret-token internal stack and private data"))
    with pytest.raises(BailingHubClientError) as caught:
        api.get_job(JOB_ID)
    assert caught.value.public_message == "BailingHub rejected the Client Token."
    assert "secret-token" not in caught.value.public_message


def test_response_size_limit_is_enforced() -> None:
    api, _ = client(FakeResponse(200, raw=b"x" * (MAX_RESPONSE_BYTES + 1)))
    with pytest.raises(BailingHubClientError, match="1 MiB"):
        api.get_job(JOB_ID)


def test_job_result_and_error_shapes_are_strict() -> None:
    api, _ = client(FakeResponse(200, {"job_id": JOB_ID, "status": "done", "result": []}))
    with pytest.raises(BailingHubClientError, match="invalid result"):
        api.get_job(JOB_ID)

    api, _ = client(
        FakeResponse(
            200,
            {"job_id": JOB_ID, "status": "error", "error": "x" * 1500},
        )
    )
    assert len(api.get_job(JOB_ID)["error"]) == 1000


def test_wait_for_job_reuses_job_id_and_returns_terminal_result(monkeypatch: Any) -> None:
    api, _ = client()
    states = iter(
        [
            {"job_id": JOB_ID, "request_id": "r1", "status": "queued", "terminal": False},
            {
                "job_id": JOB_ID,
                "request_id": "r1",
                "status": "done",
                "terminal": True,
                "result": {"ok": True},
            },
        ]
    )
    seen: list[str] = []

    def fake_get_job(job_id: str) -> dict[str, Any]:
        seen.append(job_id)
        return next(states)

    monkeypatch.setattr(api, "get_job", fake_get_job)
    result = api.wait_for_job(JOB_ID, sleep=lambda _: None, monotonic=lambda: 0.0)
    assert seen == [JOB_ID, JOB_ID]
    assert result["terminal"] is True
    assert result["wait_timed_out"] is False


def test_wait_timeout_returns_latest_state_without_resubmission(monkeypatch: Any) -> None:
    api, session = client()
    monkeypatch.setattr(
        api,
        "get_job",
        lambda _: {"job_id": JOB_ID, "status": "running", "terminal": False},
    )
    clock = iter([0.0, 2.0])
    result = api.wait_for_job(JOB_ID, max_wait_seconds=1, monotonic=lambda: next(clock))
    assert result["status"] == "running"
    assert result["wait_timed_out"] is True
    assert session.calls == []
