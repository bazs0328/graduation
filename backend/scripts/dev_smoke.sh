#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ ! -f "$ROOT_DIR/sample.md" ]; then
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

BASE_URL="${BASE_URL:-http://localhost:8000}"
SAMPLE_FILE="${SAMPLE_FILE:-$ROOT_DIR/sample.md}"

if [ ! -f "$SAMPLE_FILE" ]; then
  echo "sample.md not found at $SAMPLE_FILE"
  exit 1
fi

export BASE_URL SAMPLE_FILE

python - <<'PY'
import json
import mimetypes
import os
import urllib.request
import uuid

base_url = os.environ.get("BASE_URL", "http://localhost:8000")
sample_file = os.environ["SAMPLE_FILE"]


def step(title: str) -> None:
    print(f"==> {title}")


def http_get(path: str) -> str:
    with urllib.request.urlopen(base_url + path) as resp:
        return resp.read().decode()


def http_post(path: str) -> str:
    req = urllib.request.Request(base_url + path, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def http_post_json(path: str, payload: dict) -> str:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(base_url + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def http_post_file(path: str, file_path: str) -> str:
    boundary = uuid.uuid4().hex
    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(file_path, "rb") as handle:
        file_data = handle.read()

    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(base_url + path, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(body)))
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


step("Health")
print(http_get("/health"))

step("Upload sample.md")
upload = http_post_file("/docs/upload", sample_file)
print(upload)
doc_id = json.loads(upload).get("document_id")
print(f"document_id={doc_id}")

step("Rebuild index")
print(http_post("/index/rebuild"))

step("Search keyword")
print(http_post_json("/search", {"query": "fox", "top_k": 5}))

step("Chat question")
print(http_post_json("/chat", {"query": "fox", "top_k": 5}))
PY