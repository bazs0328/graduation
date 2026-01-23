from fastapi import FastAPI

from .settings import load_settings

app = FastAPI()
settings = load_settings()


@app.get("/health")
def health():
    return {"status": "ok"}