import json
import re
import time
from dataclasses import dataclass

from app.services.llm.base import LLMClient


MAX_CONTEXT_CHARS = 6000
DEFAULT_KEYWORDS = ["资料", "核心概念", "关键点", "重点内容"]
DEFAULT_QUESTIONS = [
    "这份资料的核心主题是什么？",
    "资料中最重要的结论有哪些？",
    "有哪些关键概念需要优先理解？",
    "我应该先从哪一部分开始学习？",
]
STOPWORDS = {
    "资料",
    "内容",
    "部分",
    "问题",
    "一个",
    "这份",
    "这些",
    "可以",
    "主要",
    "包括",
}


@dataclass
class SummaryResult:
    summary: str
    keywords: list[str]
    questions: list[str]


class SummaryCache:
    def __init__(self, ttl_seconds: int = 3600, max_items: int = 200):
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._cache: dict[int, dict] = {}

    def get(self, doc_id: int) -> dict | None:
        item = self._cache.get(doc_id)
        if not item:
            return None
        if self.ttl_seconds <= 0:
            return item
        if time.time() - item.get("ts", 0) > self.ttl_seconds:
            self._cache.pop(doc_id, None)
            return None
        return item

    def set(self, doc_id: int, data: SummaryResult) -> None:
        if len(self._cache) >= self.max_items:
            oldest = sorted(self._cache.items(), key=lambda x: x[1].get("ts", 0))[:1]
            for key, _ in oldest:
                self._cache.pop(key, None)
        self._cache[doc_id] = {
            "ts": time.time(),
            "summary": data.summary,
            "keywords": data.keywords,
            "questions": data.questions,
        }

    def invalidate(self, doc_id: int) -> None:
        self._cache.pop(doc_id, None)


def build_context(chunks: list[str], max_chars: int = MAX_CONTEXT_CHARS) -> str:
    parts = []
    total = 0
    for text in chunks:
        if not text:
            continue
        remaining = max_chars - total
        if remaining <= 0:
            break
        snippet = text[:remaining]
        parts.append(snippet)
        total += len(snippet)
    return "\n\n".join(parts).strip()


def build_summary_prompt() -> str:
    return (
        "你是学习资料助手。请基于给定资料生成摘要。\n"
        "严格要求：\n"
        "1) 只输出 JSON，不要任何额外文字。\n"
        "2) summary：3-5 句中文总结（不要逐句复述原文，避免照搬原句）。\n"
        "3) keywords：5-8 个中文关键词。\n"
        "4) questions：3-5 个可直接提问的问题。\n"
        "5) 全部内容必须为中文。\n"
        "输出 JSON 示例：\n"
        "{\n"
        "  \"summary\": \"...\",\n"
        "  \"keywords\": [\"...\"],\n"
        "  \"questions\": [\"...\"]\n"
        "}\n"
    )


def generate_summary(llm_client: LLMClient, context: str) -> SummaryResult:
    prompt = build_summary_prompt()
    response = llm_client.generate_answer(prompt, context)
    parsed = _parse_summary_response(response)
    if parsed and _contains_cjk(parsed.summary):
        return parsed
    return _fallback_summary(context, response)


def _parse_summary_response(raw: str) -> SummaryResult | None:
    if not raw:
        return None
    raw = raw.strip()
    payload = None
    if raw.startswith("{") and raw.endswith("}"):
        payload = raw
    else:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            payload = match.group(0)
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    summary = str(data.get("summary") or "").strip()
    keywords = _normalize_list(data.get("keywords"))
    questions = _normalize_list(data.get("questions"))
    if not summary:
        return None
    if not keywords:
        keywords = DEFAULT_KEYWORDS[:]
    if not questions:
        questions = DEFAULT_QUESTIONS[:3]
    return SummaryResult(summary=summary, keywords=keywords, questions=questions)


def _normalize_list(value) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _fallback_summary(context: str, raw: str) -> SummaryResult:
    title = _extract_title(context)
    list_items = _extract_list_items(context)
    cjk_keywords = _extract_cjk_keywords(context)
    latin_keywords = _extract_latin_keywords(context)

    if _contains_cjk(context):
        keywords = cjk_keywords or DEFAULT_KEYWORDS[:]
        summary = _build_structured_summary(title, list_items, keywords, [], is_cjk=True)
    else:
        keywords = cjk_keywords or ["英文资料", "标题", "结构", "列表", "要点"]
        summary = _build_structured_summary(title, list_items, keywords, latin_keywords, is_cjk=False)

    questions = _build_questions(keywords)
    return SummaryResult(summary=summary, keywords=keywords, questions=questions)


def _summarize_from_context(context: str) -> str:
    if not context:
        return ""
    text = context.replace("\n", " ").strip()
    parts = re.split(r"[。！？!?]+", text)
    sentences = [part.strip() for part in parts if part.strip()]
    if not sentences:
        return ""
    picked = sentences[:4]
    return "；".join(picked)


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _extract_title(context: str) -> str:
    for line in context.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("#"):
            return cleaned.lstrip("#").strip()[:60]
        return cleaned[:60]
    return ""


def _extract_list_items(context: str) -> list[str]:
    items: list[str] = []
    for line in context.splitlines():
        cleaned = line.strip()
        if cleaned.startswith(("-", "*", "•")):
            item = cleaned.lstrip("-*•").strip()
            if item:
                items.append(item[:80])
    return items


def _extract_cjk_keywords(context: str, limit: int = 6) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fff]{2,6}", context)
    counts: dict[str, int] = {}
    for word in words:
        if word in STOPWORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:limit]]


def _extract_latin_keywords(context: str, limit: int = 5) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\\-]{2,}", context)
    counts: dict[str, int] = {}
    for word in words:
        lowered = word.lower()
        if lowered in {"the", "and", "with", "this", "that", "over", "from", "into"}:
            continue
        counts[lowered] = counts.get(lowered, 0) + 1
    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:limit]]


def _build_structured_summary(
    title: str,
    list_items: list[str],
    keywords: list[str],
    latin_keywords: list[str],
    is_cjk: bool,
) -> str:
    title_part = f"主题为《{title}》。" if title else "主题为未命名资料。"
    list_part = ""
    if list_items:
        list_count = len(list_items)
        preview = "、".join(list_items[:3])
        list_part = f"包含 {list_count} 个列表要点（如：{preview}）。"
    keyword_part = ""
    if keywords:
        keyword_part = f"关键词侧重：{'、'.join(keywords[:3])}。"
    latin_part = ""
    if latin_keywords:
        latin_part = f"常见英文关键词：{'、'.join(latin_keywords[:3])}。"
    if not is_cjk:
        return (
            f"该资料主要为英文内容，{title_part}"
            f"{list_part}{latin_part}建议先理解主题结构，再结合中文关键词提问以获得更准确回答。"
        )
    return f"该资料{title_part}{list_part}{keyword_part}".strip()


def _build_questions(keywords: list[str]) -> list[str]:
    base = DEFAULT_QUESTIONS[:3]
    if not keywords:
        return base
    topic = keywords[0]
    return [
        f"请概括“{topic}”在资料中的核心要点。",
        f"“{topic}”相关的关键结论有哪些？",
        "这份资料最值得优先掌握的内容是什么？",
    ]
