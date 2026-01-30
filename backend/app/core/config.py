import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus


@dataclass(frozen=True)
class Settings:
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    database_url: str
    data_dir: str
    faiss_index_path: str
    faiss_mapping_path: str
    llm_provider: str
    llm_base_url: str
    llm_model: str
    llm_embedding_model: str
    llm_embedding_dim: Optional[int]
    llm_timeout: float
    llm_max_tokens: int
    deepseek_api_key: str
    llm_tools_enabled: bool
    llm_tool_whitelist: str
    llm_tool_max_calls: int
    llm_tool_timeout: float
    auto_rebuild_index: bool
    index_rebuild_debounce_seconds: float


def _build_database_url(
    mysql_host: str,
    mysql_port: int,
    mysql_user: str,
    mysql_password: str,
    mysql_database: str,
) -> str:
    password = quote_plus(mysql_password)
    return (
        "mysql+pymysql://"
        f"{mysql_user}:{password}@{mysql_host}:{mysql_port}/{mysql_database}" 
        "?charset=utf8mb4"
    )


def load_settings() -> Settings:
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user = os.getenv("MYSQL_USER", "app_user")
    mysql_password = os.getenv("MYSQL_PASSWORD", "app_pass")
    mysql_database = os.getenv("MYSQL_DATABASE", "app_db")
    data_dir = os.getenv("DATA_DIR", "data")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = _build_database_url(
            mysql_host=mysql_host,
            mysql_port=mysql_port,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            mysql_database=mysql_database,
        )

    faiss_index_path = os.path.join(data_dir, "faiss.index")
    faiss_mapping_path = os.path.join(data_dir, "mapping.json")
    llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    llm_model = os.getenv("LLM_MODEL", "deepseek-reasoner")
    llm_embedding_model = os.getenv("LLM_EMBEDDING_MODEL", "")
    embedding_dim_raw = os.getenv("LLM_EMBEDDING_DIM", "").strip()
    llm_embedding_dim = int(embedding_dim_raw) if embedding_dim_raw else None
    llm_timeout = float(os.getenv("LLM_TIMEOUT", "30"))
    llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "512"))
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    llm_tools_enabled = os.getenv("LLM_TOOLS_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
    llm_tool_whitelist = os.getenv("LLM_TOOL_WHITELIST", "calc")
    llm_tool_max_calls = int(os.getenv("LLM_TOOL_MAX_CALLS", "2"))
    llm_tool_timeout = float(os.getenv("LLM_TOOL_TIMEOUT", "5"))
    auto_rebuild_index = os.getenv("AUTO_REBUILD_INDEX", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    index_rebuild_debounce_seconds = float(os.getenv("INDEX_REBUILD_DEBOUNCE_SECONDS", "2"))

    return Settings(
        mysql_host=mysql_host,
        mysql_port=mysql_port,
        mysql_user=mysql_user,
        mysql_password=mysql_password,
        mysql_database=mysql_database,
        database_url=database_url,
        data_dir=data_dir,
        faiss_index_path=faiss_index_path,
        faiss_mapping_path=faiss_mapping_path,
        llm_provider=llm_provider,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        llm_embedding_model=llm_embedding_model,
        llm_embedding_dim=llm_embedding_dim,
        llm_timeout=llm_timeout,
        llm_max_tokens=llm_max_tokens,
        deepseek_api_key=deepseek_api_key,
        llm_tools_enabled=llm_tools_enabled,
        llm_tool_whitelist=llm_tool_whitelist,
        llm_tool_max_calls=llm_tool_max_calls,
        llm_tool_timeout=llm_tool_timeout,
        auto_rebuild_index=auto_rebuild_index,
        index_rebuild_debounce_seconds=index_rebuild_debounce_seconds,
    )
