#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
REAL_SOURCE_OBJ = (
    Path(__file__).resolve().parents[2]
    / "abc_dataset/00009490/00009490_48f21d6478e64f7d8eea685f_trimesh_001.obj"
)


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body_text: str
    body_json: Any | None


def main() -> int:
    email = f"render-e2e-{uuid4().hex[:12]}@example.com"
    password = "testpass123"

    register_response = request_json(
        "POST",
        f"{API_PREFIX}/auth/register",
        {"email": email, "password": password},
    )
    expect_status(register_response, 201)
    access_token = register_response.body_json["access_token"]

    create_run_response = request_json(
        "POST",
        f"{API_PREFIX}/runs",
        {"name": "Real Render Collage E2E"},
        token=access_token,
    )
    expect_status(create_run_response, 201)
    run_id = create_run_response.body_json["id"]

    upload_response = request_files(
        "POST",
        f"{API_PREFIX}/runs/{run_id}/source-file",
        [("file", REAL_SOURCE_OBJ)],
        token=access_token,
    )
    expect_status(upload_response, 200)
    expect_json_path(upload_response.body_json, ["status"], "source_uploaded")

    process_response = request_json(
        "POST",
        f"{API_PREFIX}/runs/{run_id}/process",
        None,
        token=access_token,
        timeout=300,
    )
    expect_status(process_response, 202)
    expect_json_path(process_response.body_json, ["status"], "rendered")
    render_artifacts = [
        artifact
        for artifact in process_response.body_json["artifacts"]
        if artifact["type"] == "render"
    ]
    if len(render_artifacts) < 6:
        raise AssertionError("expected at least 6 render artifacts after process")

    collage_response = request_json(
        "POST",
        f"{API_PREFIX}/runs/{run_id}/collages/generate",
        {"counts": [3, 4, 6], "selected_count": 6},
        token=access_token,
        timeout=120,
    )
    expect_status(collage_response, 201)
    expect_json_path(collage_response.body_json, ["status"], "collages_ready")
    expect_json_path(
        collage_response.body_json,
        ["selected_collage_artifact_id"],
        collage_id_for_size(collage_response.body_json, 6),
    )

    selected_collage_response = request_json(
        "GET",
        f"{API_PREFIX}/runs/{run_id}/selected-collage",
        None,
        token=access_token,
        timeout=60,
    )
    expect_status(selected_collage_response, 200)
    download_url = selected_collage_response.body_json["download_url"]
    if not download_url:
        raise AssertionError("selected collage is missing download_url")

    collage_bytes = download_binary(download_url, timeout=60)
    if len(collage_bytes) == 0:
        raise AssertionError("downloaded collage is empty")

    print(json.dumps(
        {
            "run_id": run_id,
            "render_artifact_count": len(render_artifacts),
            "selected_collage_artifact_id": selected_collage_response.body_json["id"],
            "selected_collage_size_bytes": len(collage_bytes),
            "download_url": download_url,
        },
        ensure_ascii=True,
        indent=2,
    ))
    return 0


def collage_id_for_size(run_payload: dict[str, Any], collage_size: int) -> int:
    for artifact in run_payload["artifacts"]:
        if artifact["type"] != "collage":
            continue
        meta_json = artifact.get("meta_json") or {}
        if meta_json.get("collage_size") == collage_size:
            return artifact["id"]
    raise AssertionError(f"collage artifact for size {collage_size} was not found")


def request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    *,
    token: str | None = None,
    timeout: int = 30,
) -> Response:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return request(method, path, data=data, headers=headers, timeout=timeout)


def request_files(
    method: str,
    path: str,
    files: list[tuple[str, Path]],
    *,
    token: str | None = None,
    timeout: int = 30,
) -> Response:
    boundary = f"----e2e{uuid4().hex}"
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return request(
        method,
        path,
        data=encode_multipart(files, boundary),
        headers=headers,
        timeout=timeout,
    )


def request(
    method: str,
    path: str,
    *,
    data: bytes | None,
    headers: dict[str, str],
    timeout: int,
) -> Response:
    url = path if path.startswith(("http://", "https://")) else f"{BASE_URL}{path}"
    request_obj = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request_obj, timeout=timeout) as response:
            body_bytes = response.read()
            return build_response(response.status, response.headers, body_bytes)
    except urllib.error.HTTPError as exc:
        return build_response(exc.code, exc.headers, exc.read())


def download_binary(url: str, *, timeout: int) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def build_response(status: int, headers: Any, body_bytes: bytes) -> Response:
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


def encode_multipart(files: list[tuple[str, Path]], boundary: str) -> bytes:
    body = bytearray()
    for field_name, path in files:
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


def expect_status(response: Response, expected_status: int) -> None:
    if response.status != expected_status:
        raise AssertionError(
            f"expected status {expected_status}, got {response.status}, body={response.body_text}"
        )


def expect_json_path(payload: Any, path: list[Any], expected: Any) -> None:
    current = payload
    for item in path:
        current = current[item]
    if current != expected:
        raise AssertionError(f"path {path} expected {expected!r}, got {current!r}")


if __name__ == "__main__":
    sys.exit(main())
