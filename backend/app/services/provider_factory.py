import logging

from app.core.config import Settings
from app.services.embeddings import HashEmbedder, RealEmbedder
from app.services.llm.mock import MockLLM
from app.services.llm.real import RealLLMClient
from app.services.provider_utils import normalize_base_url

logger = logging.getLogger(__name__)


def build_llm_client(settings: Settings):
    provider = (settings.llm_provider or "").strip().lower() or "mock"
    api_key = (settings.deepseek_api_key or "").strip()
    base_url = normalize_base_url(settings.llm_base_url)
    if provider in {"deepseek", "openai", "openai-compatible", "auto", "real"}:
        if not api_key:
            logger.warning(
                "LLM_PROVIDER=%s but DEEPSEEK_API_KEY is missing. Falling back to MockLLM.",
                provider,
            )
            return MockLLM()
        if not base_url:
            logger.warning(
                "LLM_PROVIDER=%s but LLM_BASE_URL is missing. Falling back to MockLLM.",
                provider,
            )
            return MockLLM()
        return RealLLMClient(
            base_url=base_url,
            api_key=api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout,
            max_tokens=settings.llm_max_tokens,
        )

    if provider in {"mock", "hash", "offline"}:
        return MockLLM()

    logger.warning("Unknown LLM_PROVIDER=%s. Falling back to MockLLM.", provider)
    return MockLLM()


def build_embedder(settings: Settings):
    model = (settings.llm_embedding_model or "").strip()
    api_key = (settings.deepseek_api_key or "").strip()
    hash_dim = settings.llm_embedding_dim or 384
    base_url = normalize_base_url(settings.llm_base_url)

    if model:
        if not api_key:
            logger.warning(
                "LLM_EMBEDDING_MODEL is set but DEEPSEEK_API_KEY is missing. Using HashEmbedder.",
            )
            return HashEmbedder(dim=hash_dim)
        if not base_url:
            logger.warning(
                "LLM_EMBEDDING_MODEL is set but LLM_BASE_URL is missing. Using HashEmbedder.",
            )
            return HashEmbedder(dim=hash_dim)
        if not settings.llm_embedding_dim:
            logger.warning(
                "LLM_EMBEDDING_MODEL is set but LLM_EMBEDDING_DIM is missing. Using HashEmbedder.",
            )
            return HashEmbedder(dim=hash_dim)
        return RealEmbedder(
            base_url=base_url,
            api_key=api_key,
            model=model,
            dim=settings.llm_embedding_dim,
            timeout=settings.llm_timeout,
        )

    return HashEmbedder(dim=hash_dim)
