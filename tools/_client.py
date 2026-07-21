from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_READ_TIMEOUT = 30.0
MAX_RESPONSE_BYTES = 1024 * 1024
TERMINAL_STATUSES = frozenset({"done", "error", "rejected"})
KNOWN_STATUSES = frozenset({"queued", "running", "dispatched", *TERMINAL_STATUSES})
_ROUTE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
_JOB_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class BailingHubClientError(RuntimeError):
    def __init__(
        self,
        public_message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(public_message)
        self.public_message = public_message
        self.status_code = status_code
        self.retryable = retryable


def normalize_base_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("BailingHub Base URL is required.")

    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("BailingHub Base URL must be an absolute HTTP(S) URL.")
    if parsed.username or parsed.password:
        raise ValueError("BailingHub Base URL must not contain embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("BailingHub Base URL must not contain a query string or fragment.")
    if parsed.scheme == "http" and (parsed.hostname or "").lower() not in _LOOPBACK_HOSTS:
        raise ValueError("Use HTTPS for non-loopback BailingHub connections.")

    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def require_non_empty(value: Any, name: str, *, max_length: int | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required.")
    if max_length is not None and len(text) > max_length:
        raise ValueError(f"{name} must not exceed {max_length} characters.")
    return text


class BailingHubClient:
    def __init__(
        self,
        base_url: str,
        client_token: str,
        *,
        session: requests.Session | None = None,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.client_token = require_non_empty(client_token, "BailingHub Client Token")
        self.session = session or requests.Session()
        self.timeout = (connect_timeout, read_timeout)

    @classmethod
    def from_credentials(cls, credentials: dict[str, Any]) -> BailingHubClient:
        return cls(
            base_url=str(credentials.get("base_url") or ""),
            client_token=str(credentials.get("client_token") or ""),
        )

    def validate_credentials(self) -> None:
        health = self._request("GET", "/health", authenticated=False)
        if not isinstance(health.get("status"), str):
            raise BailingHubClientError(
                "The configured URL did not return a BailingHub health response."
            )

        sentinel = "00000000-0000-0000-0000-000000000000"
        self._request("GET", f"/jobs/{sentinel}", allowed_statuses={404})

    def submit_job(self, *, request_id: Any, route: Any, input_text: Any) -> dict[str, Any]:
        normalized_request_id = require_non_empty(request_id, "request_id", max_length=128)
        normalized_route = require_non_empty(route, "route", max_length=64)
        normalized_input = require_non_empty(input_text, "input", max_length=100_000)
        if not _ROUTE_PATTERN.fullmatch(normalized_route):
            raise ValueError("route must match ^[a-z0-9][a-z0-9_-]{1,63}$.")

        body = self._request(
            "POST",
            "/run",
            json_body={
                "request_id": normalized_request_id,
                "route": normalized_route,
                "input": normalized_input,
            },
            allowed_statuses={202},
        )
        return self._normalize_job(body, require_request_id=True)

    def get_job(self, job_id: Any) -> dict[str, Any]:
        normalized_job_id = require_non_empty(job_id, "job_id", max_length=36)
        if not _JOB_ID_PATTERN.fullmatch(normalized_job_id):
            raise ValueError("job_id must be a UUID returned by BailingHub.")
        body = self._request("GET", f"/jobs/{normalized_job_id}")
        return self._normalize_job(body)

    def wait_for_job(
        self,
        job_id: Any,
        *,
        max_wait_seconds: Any = 20,
        poll_interval_seconds: Any = 2,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> dict[str, Any]:
        wait_seconds = self._bounded_number(
            max_wait_seconds, "max_wait_seconds", minimum=1, maximum=60
        )
        interval = self._bounded_number(
            poll_interval_seconds, "poll_interval_seconds", minimum=0.5, maximum=10
        )
        deadline = monotonic() + wait_seconds
        latest = self.get_job(job_id)
        while latest["status"] not in TERMINAL_STATUSES and monotonic() < deadline:
            sleep(min(interval, max(0.0, deadline - monotonic())))
            latest = self.get_job(job_id)
        return {**latest, "wait_timed_out": latest["status"] not in TERMINAL_STATUSES}

    @staticmethod
    def _bounded_number(value: Any, name: str, *, minimum: float, maximum: float) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be a number between {minimum} and {maximum}.")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a number between {minimum} and {maximum}.") from exc
        if not minimum <= number <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}.")
        return number

    def _normalize_job(
        self, body: dict[str, Any], *, require_request_id: bool = False
    ) -> dict[str, Any]:
        job_id = str(body.get("job_id") or body.get("id") or "").strip()
        status = str(body.get("status") or "").strip()
        request_id = str(body.get("request_id") or "").strip()
        if not _JOB_ID_PATTERN.fullmatch(job_id) or status not in KNOWN_STATUSES:
            raise BailingHubClientError("BailingHub returned an invalid job response.")
        if require_request_id and not request_id:
            raise BailingHubClientError("BailingHub returned a job without request_id.")
        if len(request_id) > 128:
            raise BailingHubClientError("BailingHub returned an invalid request_id.")

        normalized: dict[str, Any] = {
            "job_id": job_id,
            "request_id": request_id,
            "status": status,
            "terminal": status in TERMINAL_STATUSES,
        }
        for key in ("route", "target"):
            if key in body and body[key] is not None:
                value = body[key]
                if not isinstance(value, str) or len(value) > 300:
                    raise BailingHubClientError(f"BailingHub returned an invalid {key} value.")
                normalized[key] = value
        if body.get("result") is not None:
            if not isinstance(body["result"], dict):
                raise BailingHubClientError("BailingHub returned an invalid result value.")
            normalized["result"] = body["result"]
        if body.get("error") is not None:
            error = body["error"]
            if not isinstance(error, str):
                raise BailingHubClientError("BailingHub returned an invalid error value.")
            normalized["error"] = error[:1000]
        return normalized

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        authenticated: bool = True,
        allowed_statuses: set[int] | None = None,
    ) -> dict[str, Any]:
        expected = allowed_statuses or {200}
        headers = {
            "Accept": "application/json",
            "User-Agent": "bailinghub-dify-plugin/0.1.0",
        }
        if authenticated:
            headers["Authorization"] = f"Bearer {self.client_token}"
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                json=json_body,
                timeout=self.timeout,
                stream=True,
            )
            raw = self._read_limited(response)
        except requests.Timeout as exc:
            raise BailingHubClientError("BailingHub request timed out.", retryable=True) from exc
        except requests.RequestException as exc:
            raise BailingHubClientError("Could not connect to BailingHub.", retryable=True) from exc

        if response.status_code not in expected:
            raise self._http_error(response.status_code, raw)
        if response.status_code == 404 and 404 in expected:
            return {}
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise BailingHubClientError("BailingHub returned a non-JSON response.") from exc
        if not isinstance(decoded, dict):
            raise BailingHubClientError("BailingHub returned a non-object JSON response.")
        return decoded

    @staticmethod
    def _read_limited(response: requests.Response) -> bytes:
        chunks: list[bytes] = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise BailingHubClientError(
                        "BailingHub response exceeded the 1 MiB safety limit."
                    )
                chunks.append(chunk)
        finally:
            response.close()
        return b"".join(chunks)

    @staticmethod
    def _http_error(status_code: int, raw: bytes) -> BailingHubClientError:
        if status_code == 401:
            message = "BailingHub rejected the Client Token."
        elif status_code == 403:
            message = "The BailingHub client is not allowed to perform this operation."
        elif status_code == 404:
            message = "The BailingHub job was not found or is not owned by this client."
        elif status_code == 409:
            message = (
                "BailingHub rejected the request because of an idempotency or routing conflict."
            )
        elif status_code == 429:
            message = (
                "The BailingHub client rate limit was exceeded. Retry the same request_id later."
            )
        elif status_code >= 500:
            message = "BailingHub is temporarily unavailable."
        else:
            message = f"BailingHub rejected the request (HTTP {status_code})."

        # Only surface the documented short error value, never an arbitrary response body.
        if status_code in {400, 409} and len(raw) <= 4096:
            try:
                decoded = json.loads(raw.decode("utf-8"))
                detail = decoded.get("error") if isinstance(decoded, dict) else None
                if isinstance(detail, str) and 0 < len(detail) <= 300:
                    message = f"{message} {detail}"
            except (UnicodeDecodeError, ValueError):
                pass
        return BailingHubClientError(
            message,
            status_code=status_code,
            retryable=status_code in {408, 425, 429} or status_code >= 500,
        )
