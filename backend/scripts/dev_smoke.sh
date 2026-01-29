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


def http_get(path: str, headers: dict | None = None) -> str:
    req = urllib.request.Request(base_url + path, method="GET")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def http_post(path: str, headers: dict | None = None) -> str:
    req = urllib.request.Request(base_url + path, method="POST")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def http_post_json(path: str, payload: dict, headers: dict | None = None) -> str:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(base_url + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
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
chat_raw = http_post_json("/chat", {"query": "fox", "top_k": 5})
print(chat_raw)
chat_data = json.loads(chat_raw)

step("Chat tool calc")
tool_chat_raw = http_post_json("/chat", {"query": "calc: 2+2", "top_k": 1})
print(tool_chat_raw)
tool_chat = json.loads(tool_chat_raw)
tool_traces = tool_chat.get("tool_traces") or []
if not tool_traces:
    raise SystemExit("tool_traces missing from /chat")


def resolve_sources(label: str, chunk_ids: list[int]) -> list[dict]:
    step(label)
    if not chunk_ids:
        print("chunk_ids missing; skip sources resolve")
        return []
    resolved_raw = http_post_json(
        "/sources/resolve",
        {"chunk_ids": chunk_ids, "preview_len": 120},
    )
    print(resolved_raw)
    resolved = json.loads(resolved_raw)
    items = resolved.get("items") or []
    if not items:
        raise SystemExit("sources resolve returned empty")
    return items


chat_chunk_ids = [
    item.get("chunk_id")
    for item in (chat_data.get("sources") or [])
    if isinstance(item, dict) and item.get("chunk_id") is not None
]
resolve_sources("Chat sources resolve", chat_chunk_ids)

def generate_quiz(session_id: str, label: str = "Quiz generate") -> tuple[int | None, list, dict]:
    step(f"{label} ({session_id})")
    if not doc_id:
        print("document_id missing; skip quiz generate")
        return None, [], {}
    headers = {"X-Session-Id": session_id}
    quiz_payload = http_post_json(
        "/quiz/generate",
        {"document_id": doc_id, "count": 5, "types": ["single", "judge", "short"]},
        headers=headers,
    )
    print(quiz_payload)
    quiz = json.loads(quiz_payload)
    quiz_id = quiz.get("quiz_id")
    questions = quiz.get("questions") or []
    plan = quiz.get("difficulty_plan") or {}
    print(f"quiz_id={quiz_id}")
    print(f"question_count={len(questions)}")
    print(f"difficulty_plan={plan}")
    if len(questions) < 5:
        raise SystemExit("quiz question count < 5")
    first_sources = []
    if questions and isinstance(questions[0], dict):
        first_sources = questions[0].get("source_chunk_ids") or []
    resolve_sources("Quiz sources resolve", first_sources)
    return quiz_id, questions, plan


def build_answers(question_items, make_wrong: bool) -> list[dict]:
    results = []
    used_wrong = False
    for item in question_items:
        qid = item.get("question_id")
        qtype = item.get("type")
        expected = item.get("answer") if isinstance(item, dict) else None
        if qid is None:
            continue
        if qtype == "single":
            choice = expected.get("choice") if isinstance(expected, dict) else "A"
            wrong_choice = "B" if choice != "B" else "C"
            if make_wrong or not used_wrong:
                user_answer = {"choice": wrong_choice}
                used_wrong = True
            else:
                user_answer = {"choice": choice or "A"}
        elif qtype == "judge":
            expected_value = expected.get("value") if isinstance(expected, dict) else True
            if make_wrong or not used_wrong:
                user_answer = {"value": not bool(expected_value)}
                used_wrong = True
            else:
                user_answer = {"value": bool(expected_value)}
        else:
            user_answer = {"text": "self-review"}
        results.append({"question_id": qid, "user_answer": user_answer})
    return results


def submit_and_profile(session_id: str, mode: str) -> None:
    quiz_id, questions, plan = generate_quiz(session_id, "Quiz generate (initial)")
    step(f"Quiz submit ({session_id})")
    if not quiz_id or not questions:
        print("quiz_id missing; skip quiz submit")
        return
    headers = {"X-Session-Id": session_id}
    if mode == "good":
        answers = build_answers(questions, make_wrong=False)
    else:
        answers = build_answers(questions, make_wrong=True)
    submit_payload = {"quiz_id": quiz_id, "answers": answers}
    submit_raw = http_post_json("/quiz/submit", submit_payload, headers=headers)
    print(submit_raw)
    submit_data = json.loads(submit_raw)
    print(f"score={submit_data.get('score')} accuracy={submit_data.get('accuracy')}")
    if submit_data.get("score") is None or submit_data.get("accuracy") is None:
        raise SystemExit("submit missing score/accuracy")
    print(http_post_json("/quiz/submit", submit_payload, headers=headers))
    step(f"Profile me ({session_id})")
    profile_raw = http_get("/profile/me", headers=headers)
    print(profile_raw)
    profile = json.loads(profile_raw)
    print(
        "profile_ability="
        + str(profile.get("ability_level"))
        + " frustration="
        + str(profile.get("frustration_score"))
    )
    last_summary = profile.get("last_quiz_summary") if isinstance(profile, dict) else None
    if isinstance(last_summary, dict):
        print(f"profile_last_accuracy={last_summary.get('accuracy')}")
        recommendation = last_summary.get("next_quiz_recommendation")
        if recommendation:
            print(f"profile_recommendation={recommendation}")
        if mode == "bad" and recommendation != "easy_first":
            raise SystemExit("profile missing easy_first recommendation")
    elif mode == "bad":
        raise SystemExit("profile missing last_quiz_summary")
    if mode == "bad":
        _, _, next_plan = generate_quiz(session_id, "Quiz generate (after overhard)")
        print(f"next_difficulty_plan={next_plan}")
        if next_plan.get("Hard", 0) != 0 or next_plan.get("Easy", 0) < 4:
            raise SystemExit("overhard fallback not applied")


submit_and_profile("session-good", "good")
submit_and_profile("session-bad", "bad")
step("Quiz recent (session-good)")
recent_raw = http_post_json(
    "/quizzes/recent",
    {"limit": 5},
    headers={"X-Session-Id": "session-good"},
)
print(recent_raw)
recent_data = json.loads(recent_raw)
if not isinstance(recent_data.get("items"), list):
    raise SystemExit("recent quizzes missing items list")

def research_flow(session_id: str) -> None:
    headers = {"X-Session-Id": session_id}
    step(f"Research create ({session_id})")
    create_raw = http_post_json(
        "/research",
        {"title": "Smoke research", "summary": "Store traces and sources"},
        headers=headers,
    )
    print(create_raw)
    create_data = json.loads(create_raw)
    research_id = create_data.get("research_id")
    if not research_id:
        raise SystemExit("research create missing research_id")

    step(f"Research append ({session_id})")
    entry_raw = http_post_json(
        f"/research/{research_id}/entries",
        {
            "entry_type": "note",
            "content": "First note",
            "tool_traces": [{"tool_name": "calc", "input": {"expression": "2+2"}, "output": "4"}],
            "sources": [
                {
                    "chunk_id": 1,
                    "document_id": 1,
                    "document_name": "sample.md",
                    "text_preview": "Sample preview",
                }
            ],
        },
        headers=headers,
    )
    print(entry_raw)
    entry_data = json.loads(entry_raw)
    if not entry_data.get("entry_id"):
        raise SystemExit("research append missing entry_id")

    step(f"Research list ({session_id})")
    list_raw = http_get("/research", headers=headers)
    print(list_raw)
    list_data = json.loads(list_raw)
    if not isinstance(list_data.get("items"), list):
        raise SystemExit("research list missing items list")

    step(f"Research detail ({session_id})")
    detail_raw = http_get(f"/research/{research_id}", headers=headers)
    print(detail_raw)
    detail_data = json.loads(detail_raw)
    entries = detail_data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SystemExit("research detail missing entries")


research_flow("session-good")
PY
