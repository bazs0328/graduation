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

### Health check

```
curl http://localhost:8000/health
```

Expected response:

```
{"status":"ok"}
```
