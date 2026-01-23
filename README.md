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

### Health check

```
curl http://localhost:8000/health
```

Expected response:

```
{"status":"ok"}
```