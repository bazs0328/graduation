# graduation

## Backend MVP (Phase 1)

### Start

1) (Optional) create local env file

   ```
   cp .env.example .env
   ```

2) Build and run

   ```
   docker compose up --build
   ```

### Migrations (Alembic)

Run migrations inside the backend container:

```
docker compose exec backend alembic upgrade head
```

Rollback one step:

```
docker compose exec backend alembic downgrade -1
```

Notes:
- `DATABASE_URL` is supported (optional). If not set, it falls back to `MYSQL_*` variables.

### Phase 2 schema verification (quiz/profile)

After migrating, insert and query a quiz + question + profile:

```
docker compose exec backend python /app/scripts/verify_quiz_schema.py
```

Expected output includes `quiz_id`, `question_id`, and `profile_id`.

### Upload a document

Markdown example:

```
curl -F "file=@sample.md" http://localhost:8000/docs/upload
```

Fetch document metadata:

```
curl http://localhost:8000/docs/{id}
```

### Document summary (LLM, on-demand)

Generate a Chinese summary, keywords, and suggested questions:

```
curl -X POST http://localhost:8000/docs/{id}/summary \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

Response example:

```
{"document_id":1,"summary":"...","keywords":["..."],"questions":["..."],"cached":false}
```

Debug trace (prompt + raw output + fallback):

```
curl -X POST "http://localhost:8000/docs/{id}/summary" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

Error example (no chunks / empty doc):

```
{"code":"DOC_EMPTY","message":"Document has no chunks","details":{"document_id":1}}
```

### Build FAISS index

Rebuild index from all chunks:

```
curl -X POST http://localhost:8000/index/rebuild
```

Notes:
- Index files are persisted under `backend/data` (mounted to `/app/data` in the container).
- On startup, the backend will load the index if present, otherwise it logs that rebuild is required.

### Search (no LLM)

```
curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d '{"query":"sample","top_k":5,"document_id":1}'
```

### Chat (minimal RAG)

```
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"query":"sample","top_k":5,"document_id":1}'
```

Notes:
- 若启用工具链（LLM_TOOLS_ENABLED=1），/chat 会返回 `tool_traces` 记录工具调用轨迹。
- 当资料无直接命中时，/chat 会基于语义召回给出候选并附改写建议。
- document_id 传入时仅在该文档范围内检索；若向量召回为空，系统会在文档内进行原词兜底匹配。

Response example (structured):

```
{
  "answer": "叶公好龙，比喻表面上爱好某事物，实际上并不是真的爱好。",
  "structured": {
    "conclusion": "叶公好龙，比喻表面上爱好某事物，实际上并不是真的爱好。",
    "evidence": [{"chunk_id": 8, "quote": "叶公非常喜欢龙，他在衣带钩上雕着龙..."}],
    "reasoning": "资料显示叶公只喜装饰龙，真龙现身便惊恐逃跑。",
    "next_steps": ["解释一下 叶公 的核心概念", "叶公 的关键结论有哪些？"]
  },
  "sources": [{"chunk_id": 8, "document_id": 8, "score": 0.12, "match_mode": "exact"}],
  "tool_traces": [],
  "retrieval": {"mode": "exact", "reason": "exact_match", "suggestions": ["解释一下 叶公 的核心概念"]}
}
```

### Tool calls (safe calc)

Enable tools (default on in `.env.example`):

```
LLM_TOOLS_ENABLED=1
LLM_TOOL_WHITELIST=calc
```

Example:

```
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"query":"calc: 2+2","top_k":1}'
```

Response example:

```
{"answer":"计算结果：4","sources":[],"tool_traces":[{"tool_name":"calc","input":{"expression":"2+2"},"output":"4","error":null,"duration_ms":1}]}
```

### Sources resolve (citation metadata)

Resolve chunk ids to document name + text preview:

```
curl -X POST http://localhost:8000/sources/resolve -H "Content-Type: application/json" -d '{"chunk_ids":[1,2],"preview_len":120}'
```

Response example:

```
{"items":[{"chunk_id":1,"document_id":1,"document_name":"sample.md","text_preview":"# Sample Markdown This is a small sample file..."}],"missing_chunk_ids":[]}
```

Error (example):

```
{"code":404,"message":"Sources not found","details":{"missing_chunk_ids":[999]}}
```

### Research / Notebook (Phase 4)

Create a research session:

```
curl -X POST http://localhost:8000/research -H "Content-Type: application/json" -H "X-Session-Id: demo" -d '{"title":"RAG reliability","summary":"Collect tool outputs and citations."}'
```

Response example:

```
{"research_id":1,"session_id":"demo","title":"RAG reliability","summary":"Collect tool outputs and citations.","created_at":"2026-01-29T11:05:00","updated_at":"2026-01-29T11:05:00"}
```

Append a notebook entry:

```
curl -X POST http://localhost:8000/research/1/entries -H "Content-Type: application/json" -H "X-Session-Id: demo" -d '{"entry_type":"note","content":"Initial findings","tool_traces":[{"tool_name":"calc","input":{"expression":"2+2"},"output":"4"}],"sources":[{"chunk_id":1,"document_id":1,"document_name":"sample.md","text_preview":"# Sample Markdown..."}]}'
```

Response example:

```
{"entry_id":1,"research_id":1,"entry_type":"note","content":"Initial findings","tool_traces":[{"tool_name":"calc","input":{"expression":"2+2"},"output":"4"}],"sources":[{"chunk_id":1,"document_id":1,"document_name":"sample.md","text_preview":"# Sample Markdown..."}],"created_at":"2026-01-29T11:06:00"}
```

List research sessions:

```
curl -H "X-Session-Id: demo" http://localhost:8000/research
```

Response example:

```
{"items":[{"research_id":1,"title":"RAG reliability","summary":"Collect tool outputs and citations.","entry_count":1,"created_at":"2026-01-29T11:05:00","updated_at":"2026-01-29T11:06:00"}]}
```

Research detail:

```
curl -H "X-Session-Id: demo" http://localhost:8000/research/1
```

Notes:
- `entry_type` is a free label (e.g., `question`, `analysis`, `note`, `tool`).
- `sources` can include `document_name` and `text_preview` for UI replay.
- `X-Session-Id` is required for all `/research` endpoints; missing header returns 400.
- Session mismatch returns 403 with `{code,message,details}`; missing id returns 404.

### Quiz generate (LLM enhanced)

```
curl -X POST http://localhost:8000/quiz/generate -H "Content-Type: application/json" -d '{"document_id":1,"count":5,"types":["single","judge","short","fill_blank","calculation","written"]}'
```

Notes:
- `/quiz/generate` 返回 `difficulty_plan` 并写入 quizzes.difficulty_plan_json；初学者 Hard=0，Easy 占比更高。
- 每题会附带 `difficulty_reason` / `key_points` / `review_suggestion` / `next_step` / `validation(kb_coverage,extension_points)` 用于结果页展示。

### Quiz submit (Phase 2 MVP)

```
curl -X POST http://localhost:8000/quiz/submit -H "Content-Type: application/json" -d '{"quiz_id":1,"answers":[{"question_id":1,"user_answer":{"choice":"A"}},{"question_id":2,"user_answer":{"value":true}},{"question_id":3,"user_answer":{"text":"self-review"}}]}'
```

Notes:
- `user_answer` is required for every question; short questions are not auto-graded and return a reference answer for self-review.
- `X-Session-Id` must match the quiz session; mismatch returns 403 with `{code,message,details}`.
- 若 accuracy < 30% 或前 5 道客观题错 >= 4，会追加鼓励反馈并在 last_quiz_summary 写入 `next_quiz_recommendation=easy_first`，下次生成更保守。

### Quiz recent (history list)

```
curl -X POST http://localhost:8000/quizzes/recent -H "Content-Type: application/json" -H "X-Session-Id: default" -d '{"limit":5}'
```

Response example:

```
{"items":[{"quiz_id":1,"submitted_at":"2026-01-26T08:40:09","score":3.0,"accuracy":0.75,"difficulty_plan":{"Easy":3,"Medium":2,"Hard":0},"summary":{"score":3.0,"accuracy":0.75}}]}
```

Notes:
- limit 默认 5，范围 1-20；无记录时返回空数组。

### Profile (Phase 2 MVP)

Default session:

```
curl http://localhost:8000/profile/me
```

Custom session:

```
curl -H "X-Session-Id: demo-session" http://localhost:8000/profile/me
```

Notes:
- /quiz/submit 会更新 concept_stats，/profile/me 的 weak_concepts 按 wrong_count 排序展示弱项概览。
- 画像更新基于近期提交的客观题准确率：<50% beginner，50–80% intermediate，>=80% advanced；连续错会提升 frustration_score。

### Dev scripts

Run smoke test (requires docker compose already running):

```
bash backend/scripts/dev_smoke.sh
```

Run inside container (no local bash required):

```
docker compose exec backend sh /app/scripts/dev_smoke.sh
```

PowerShell alternative (Windows):

```
powershell -ExecutionPolicy Bypass -File backend/scripts/dev_smoke.ps1
```

### LLM Provider (Deepseek, OpenAI-compatible)

Default uses MockLLM + HashEmbedder. To enable Deepseek, only `DEEPSEEK_API_KEY` is required
(base URL/model已给默认值，可按需覆盖)：

```
DEEPSEEK_API_KEY=your_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-reasoner
```

Notes:
- docker compose 会读取根目录 `.env` 并注入到 backend 容器。
- 未配置 `DEEPSEEK_API_KEY` 时自动回退 Mock/Hash，保证可运行。
- 如需真实向量，请额外设置：
  - `LLM_EMBEDDING_MODEL=your_embedding_model`
  - `LLM_EMBEDDING_DIM=embedding_dim`
  - 改动后需 `POST /index/rebuild` 重新建索引。

## Frontend MVP (Phase 3)

### Setup (React + Vite)

From repo root:

```
cd frontend
cp .env.example .env
npm install
npm run dev
```

Notes:
- Default API base URL is `http://localhost:8000` via `VITE_API_BASE_URL`.
- If the frontend runs on a different origin, set `CORS_ORIGINS` for the backend:
  - Example: `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

### Use the MVP

1) Upload a document
2) Rebuild the index
3) Ask a question
4) Generate + submit a quiz
5) Load profile
6) View learning path
7) View dashboard (recent quizzes)
8) Create a research notebook and append entries

Notes:
- 测验提交后展示得分/准确率/逐题结果、难度计划与推荐信息（来源 /profile/me）。
- 学习路径基于 /profile/me 的 weak_concepts 与 last_quiz_summary 规则生成。
- 仪表盘通过 /quizzes/recent 获取最近 5 次测验记录。
- 研究记录页面要求填写会话 ID，并在 /research 中创建与追加条目。

### Phase 2 验收（端到端）

```
docker compose up -d --build backend
docker compose exec backend sh /app/scripts/dev_smoke.sh
docker compose exec backend pytest
```

Expected output includes:
- quiz_id / question_count / difficulty_plan
- score / accuracy
- profile ability / frustration / last_quiz_summary（session-bad 含 easy_first 推荐）

Reset DB + remove local index files (dev only):

```
bash backend/scripts/reset_db.sh
```

PowerShell alternative (Windows):

```
powershell -ExecutionPolicy Bypass -File backend/scripts/reset_db.ps1
```

### Tests (pytest)

Run from inside the backend container:

```
docker compose exec backend pytest
```

### Health check

```
curl http://localhost:8000/health
```

Expected response:

```
{"status":"ok"}
```

### Phase 1 自检清单

- 接口清单是否齐全：GET `/health`、POST `/docs/upload`、POST `/index/rebuild`、POST `/search`、POST `/chat`
- 上传→入库→建索引→检索→问答 是否已跑通：运行 `backend/scripts/dev_smoke.sh` 或 `backend/scripts/dev_smoke.ps1`
- 重启后索引加载/可重建是否可用：`docker compose restart backend` 后查看启动日志，必要时执行 `curl -X POST http://localhost:8000/index/rebuild`
- 错误是否明确：索引未建时 `/search` 与 `/chat` 返回 409（提示先 `/index/rebuild`）
- 是否提供可复现的 curl 或脚本：README 中的 curl 示例与 dev_smoke 脚本可直接复制运行
