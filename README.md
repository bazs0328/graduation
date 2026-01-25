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
curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d '{"query":"sample","top_k":5}'
```

### Chat (minimal RAG)

```
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"query":"sample","top_k":5}'
```

### Profile (Phase 2 MVP)

Default session:

```
curl http://localhost:8000/profile/me
```

Custom session:

```
curl -H "X-Session-Id: demo-session" http://localhost:8000/profile/me
```

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
