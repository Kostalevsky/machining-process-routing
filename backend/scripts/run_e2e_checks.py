#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import sys
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "e2e-results"
TMP_DIR = RESULTS_DIR / "tmp"


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body_text: str
    body_json: Any | None


@dataclass
class Context:
    access_token: str | None = None
    refresh_token: str | None = None
    user_id: int | None = None
    user_email: str | None = None
    run_id: int | None = None
    empty_run_id: int | None = None


class E2ERunner:
    def __init__(self) -> None:
        self.context = Context()
        self.lines: list[str] = []
        self.results: list[dict[str, Any]] = []
        self.started_at = datetime.now(UTC)
        self.case_index = 0

    def run(self) -> int:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        TMP_DIR.mkdir(parents=True, exist_ok=True)

        self._log(f"E2E started at {self.started_at.isoformat()}")
        self._log(f"Base URL: {BASE_URL}")

        cases = [
            ("healthcheck", self.case_healthcheck),
            ("openapi", self.case_openapi),
            ("register_user", self.case_register_user),
            ("duplicate_register", self.case_duplicate_register),
            ("login_success", self.case_login_success),
            ("login_bad_password", self.case_login_bad_password),
            ("refresh_success", self.case_refresh_success),
            ("refresh_with_access_token_fails", self.case_refresh_with_access_token_fails),
            ("me_requires_auth", self.case_me_requires_auth),
            ("me_success", self.case_me_success),
            ("create_empty_run", self.case_create_empty_run),
            ("process_without_source_fails", self.case_process_without_source_fails),
            ("create_main_run", self.case_create_main_run),
            ("list_runs_contains_created_runs", self.case_list_runs_contains_created_runs),
            ("get_run_success", self.case_get_run_success),
            ("upload_requires_obj_extension", self.case_upload_requires_obj_extension),
            ("upload_rejects_empty_file", self.case_upload_rejects_empty_file),
            ("upload_source_success", self.case_upload_source_success),
            ("upload_source_twice_fails", self.case_upload_source_twice_fails),
            ("process_success", self.case_process_success),
            ("process_twice_fails", self.case_process_twice_fails),
            ("get_run_after_process", self.case_get_run_after_process),
        ]

        failed = 0
        for name, fn in cases:
            self.case_index += 1
            try:
                details = fn()
                self.results.append({"name": name, "status": "passed", "details": details})
                self._log(f"[{self.case_index:02d}] PASS {name}: {details}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                details = f"{exc.__class__.__name__}: {exc}"
                self.results.append({"name": name, "status": "failed", "details": details})
                self._log(f"[{self.case_index:02d}] FAIL {name}: {details}")
                self._log(traceback.format_exc())

        finished_at = datetime.now(UTC)
        passed = len(self.results) - failed
        summary = {
            "base_url": BASE_URL,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "passed": passed,
            "failed": failed,
            "results": self.results,
        }
        self._log(f"Summary: {passed} passed, {failed} failed")
        self._write_reports(summary)
        return 1 if failed else 0

    def case_healthcheck(self) -> str:
        response = self._request("GET", "/api/v1/health")
        self._expect_status(response, 200)
        self._expect_json_path(response.body_json, ["status"], "ok")
        return "health endpoint returned ok"

    def case_openapi(self) -> str:
        response = self._request("GET", "/openapi.json")
        self._expect_status(response, 200)
        paths = response.body_json.get("paths", {})
        required_paths = [
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/runs",
            "/api/v1/runs/{run_id}/source-file",
            "/api/v1/runs/{run_id}/process",
        ]
        for path in required_paths:
            if path not in paths:
                raise AssertionError(f"OpenAPI path missing: {path}")
        return "required OpenAPI paths are present"

    def case_register_user(self) -> str:
        email = f"e2e-{uuid4().hex[:12]}@example.com"
        response = self._request(
            "POST",
            f"{API_PREFIX}/auth/register",
            json_body={"email": email, "password": "testpass123"},
        )
        self._expect_status(response, 201)
        self.context.access_token = response.body_json["access_token"]
        self.context.refresh_token = response.body_json["refresh_token"]
        self.context.user_id = response.body_json["user"]["id"]
        self.context.user_email = email
        return f"registered user_id={self.context.user_id} email={email}"

    def case_duplicate_register(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/auth/register",
            json_body={"email": self.context.user_email, "password": "testpass123"},
        )
        self._expect_status(response, 409)
        return "duplicate email rejected with 409"

    def case_login_success(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/auth/login",
            json_body={"email": self.context.user_email, "password": "testpass123"},
        )
        self._expect_status(response, 200)
        self.context.access_token = response.body_json["access_token"]
        self.context.refresh_token = response.body_json["refresh_token"]
        return "login returned access and refresh tokens"

    def case_login_bad_password(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/auth/login",
            json_body={"email": self.context.user_email, "password": "wrongpass123"},
        )
        self._expect_status(response, 401)
        return "bad password rejected with 401"

    def case_refresh_success(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/auth/refresh",
            json_body={"refresh_token": self.context.refresh_token},
        )
        self._expect_status(response, 200)
        self.context.access_token = response.body_json["access_token"]
        self.context.refresh_token = response.body_json["refresh_token"]
        return "refresh token exchange succeeded"

    def case_refresh_with_access_token_fails(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/auth/refresh",
            json_body={"refresh_token": self.context.access_token},
        )
        self._expect_status(response, 401)
        return "access token cannot be used as refresh token"

    def case_me_requires_auth(self) -> str:
        response = self._request("GET", f"{API_PREFIX}/users/me")
        self._expect_status(response, 401)
        return "users/me requires authorization"

    def case_me_success(self) -> str:
        response = self._request("GET", f"{API_PREFIX}/users/me", token=self.context.access_token)
        self._expect_status(response, 200)
        self._expect_json_path(response.body_json, ["email"], self.context.user_email)
        return f"users/me returned {self.context.user_email}"

    def case_create_empty_run(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs",
            json_body={"name": "E2E Empty Run"},
            token=self.context.access_token,
        )
        self._expect_status(response, 201)
        self.context.empty_run_id = response.body_json["id"]
        self._expect_json_path(response.body_json, ["status"], "created")
        return f"created empty run_id={self.context.empty_run_id}"

    def case_process_without_source_fails(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs/{self.context.empty_run_id}/process",
            token=self.context.access_token,
        )
        self._expect_status(response, 409)
        return "cannot process run without source artifact"

    def case_create_main_run(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs",
            json_body={"name": "E2E Main Run"},
            token=self.context.access_token,
        )
        self._expect_status(response, 201)
        self.context.run_id = response.body_json["id"]
        self._expect_json_path(response.body_json, ["events", 0, "event_type"], "run_created")
        return f"created main run_id={self.context.run_id}"

    def case_list_runs_contains_created_runs(self) -> str:
        response = self._request("GET", f"{API_PREFIX}/runs", token=self.context.access_token)
        self._expect_status(response, 200)
        run_ids = {item["id"] for item in response.body_json}
        missing = {self.context.run_id, self.context.empty_run_id} - run_ids
        if missing:
            raise AssertionError(f"list runs missing ids: {sorted(missing)}")
        return f"list returned run_ids={sorted(run_ids)}"

    def case_get_run_success(self) -> str:
        response = self._request(
            "GET",
            f"{API_PREFIX}/runs/{self.context.run_id}",
            token=self.context.access_token,
        )
        self._expect_status(response, 200)
        self._expect_json_path(response.body_json, ["id"], self.context.run_id)
        self._expect_json_path(response.body_json, ["status"], "created")
        return "main run returned before upload"

    def case_upload_requires_obj_extension(self) -> str:
        txt_path = TMP_DIR / "invalid-upload.txt"
        txt_path.write_text("not-an-obj", encoding="utf-8")
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs/{self.context.run_id}/source-file",
            token=self.context.access_token,
            files={"file": txt_path},
        )
        self._expect_status(response, 400)
        return "non-.obj file rejected"

    def case_upload_rejects_empty_file(self) -> str:
        empty_obj = TMP_DIR / "empty.obj"
        empty_obj.write_text("", encoding="utf-8")
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs/{self.context.run_id}/source-file",
            token=self.context.access_token,
            files={"file": empty_obj},
        )
        self._expect_status(response, 400)
        return "empty .obj file rejected"

    def case_upload_source_success(self) -> str:
        obj_path = TMP_DIR / "smoke-model.obj"
        obj_path.write_text(
            "o TestModel\nv 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nf 1 2 3\n",
            encoding="utf-8",
        )
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs/{self.context.run_id}/source-file",
            token=self.context.access_token,
            files={"file": obj_path},
        )
        self._expect_status(response, 200)
        self._expect_json_path(response.body_json, ["status"], "source_uploaded")
        self._expect_json_path(response.body_json, ["artifacts", 0, "type"], "source_obj")
        return f"uploaded source artifact_id={response.body_json['source_artifact_id']}"

    def case_upload_source_twice_fails(self) -> str:
        obj_path = TMP_DIR / "second.obj"
        obj_path.write_text(
            "o TestModel\nv 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nf 1 2 3\n",
            encoding="utf-8",
        )
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs/{self.context.run_id}/source-file",
            token=self.context.access_token,
            files={"file": obj_path},
        )
        self._expect_status(response, 409)
        return "second source upload rejected"

    def case_process_success(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs/{self.context.run_id}/process",
            token=self.context.access_token,
        )
        self._expect_status(response, 202)
        self._expect_json_path(response.body_json, ["status"], "rendering")
        event_types = [event["event_type"] for event in response.body_json["events"]]
        if "render_started" not in event_types:
            raise AssertionError("render_started event missing after process")
        return "process endpoint switched run to rendering"

    def case_process_twice_fails(self) -> str:
        response = self._request(
            "POST",
            f"{API_PREFIX}/runs/{self.context.run_id}/process",
            token=self.context.access_token,
        )
        self._expect_status(response, 409)
        return "second process call rejected while rendering"

    def case_get_run_after_process(self) -> str:
        response = self._request(
            "GET",
            f"{API_PREFIX}/runs/{self.context.run_id}",
            token=self.context.access_token,
        )
        self._expect_status(response, 200)
        self._expect_json_path(response.body_json, ["status"], "rendering")
        if response.body_json["source_artifact_id"] is None:
            raise AssertionError("source_artifact_id is missing after successful upload")
        event_types = [event["event_type"] for event in response.body_json["events"]]
        required = {"run_created", "source_uploaded", "render_started"}
        if not required.issubset(set(event_types)):
            raise AssertionError(f"missing events: {sorted(required - set(event_types))}")
        return "final run state persisted as rendering with expected events"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        token: str | None = None,
        files: dict[str, Path] | None = None,
    ) -> Response:
        url = self._build_url(path)
        headers: dict[str, str] = {}
        data: bytes | None = None

        if token:
            headers["Authorization"] = f"Bearer {token}"

        if files:
            boundary = f"----e2e{uuid4().hex}"
            data = self._encode_multipart(files, boundary)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url=url, method=method, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body_bytes = response.read()
                return self._build_response(response.status, response.headers, body_bytes)
        except urllib.error.HTTPError as exc:
            body_bytes = exc.read()
            return self._build_response(exc.code, exc.headers, body_bytes)

    def _encode_multipart(self, files: dict[str, Path], boundary: str) -> bytes:
        body = bytearray()
        for field_name, path in files.items():
            content = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                (
                    "Content-Disposition: form-data; "
                    f'name="{field_name}"; filename="{path.name}"\r\n'
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode()
            )
            body.extend(content)
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())
        return bytes(body)

    def _build_response(self, status: int, headers: Any, body_bytes: bytes) -> Response:
        body_text = body_bytes.decode("utf-8", errors="replace")
        body_json: Any | None = None
        if body_text:
            try:
                body_json = json.loads(body_text)
            except json.JSONDecodeError:
                body_json = None
        return Response(
            status=status,
            headers=dict(headers.items()),
            body_text=body_text,
            body_json=body_json,
        )

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{BASE_URL}{path}"

    def _expect_status(self, response: Response, expected_status: int) -> None:
        if response.status != expected_status:
            raise AssertionError(
                "expected status "
                f"{expected_status}, got {response.status}, body={response.body_text}"
            )

    def _expect_json_path(self, payload: Any, path: list[Any], expected: Any) -> None:
        current = payload
        for item in path:
            current = current[item]
        if current != expected:
            raise AssertionError(f"path {path} expected {expected!r}, got {current!r}")

    def _log(self, message: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        self.lines.append(f"{timestamp} {message}")

    def _write_reports(self, summary: dict[str, Any]) -> None:
        timestamp = self.started_at.strftime("%Y%m%d-%H%M%S")
        text_report_path = RESULTS_DIR / f"e2e-{timestamp}.log"
        json_report_path = RESULTS_DIR / f"e2e-{timestamp}.json"
        latest_text_path = RESULTS_DIR / "latest.log"
        latest_json_path = RESULTS_DIR / "latest.json"

        text = "\n".join(self.lines) + "\n"
        text_report_path.write_text(text, encoding="utf-8")
        json_payload = json.dumps(summary, ensure_ascii=True, indent=2) + "\n"
        json_report_path.write_text(json_payload, encoding="utf-8")
        latest_text_path.write_text(text, encoding="utf-8")
        latest_json_path.write_text(json_payload, encoding="utf-8")

        print(f"Text report: {text_report_path}")
        print(f"JSON report: {json_report_path}")
        print(f"Latest text report: {latest_text_path}")
        print(f"Latest JSON report: {latest_json_path}")


def main() -> int:
    runner = E2ERunner()
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
