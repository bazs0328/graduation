from __future__ import annotations


def normalize_base_url(base_url: str) -> str:
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        return ""
    if cleaned.endswith("/v1"):
        return cleaned
    return f"{cleaned}/v1"
