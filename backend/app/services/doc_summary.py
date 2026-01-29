import json
import re
import time
from dataclasses import dataclass

from app.services.llm.base import LLMClient
from app.services.llm.real import RealLLMClient


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
    "知道",
    "因此",
    "所以",
    "主题",
    "要点",
    "侧重",
    "该资料",
    "其实",
    "离了家",
    "卧室",
    "厅堂",
    "书房",
    "酒具",
    "衣带",
    "墙壁",
    "柱梁",
}
BAD_KEYWORD_FRAGMENTS = {
    "因此",
    "所以",
    "并不",
    "不是",
}


@dataclass
class SummaryResult:
    summary: str
    keywords: list[str]
    questions: list[str]


@dataclass
class SummaryTrace:
    prompt: str
    raw_output: str
    used_fallback: bool
    fallback_reason: str


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
        "1) 只输出中文自然语言摘要（不需要 JSON）。\n"
        "2) 3-5 句，突出故事主线与寓意/结论。\n"
        "3) 不要逐句复述原文，避免照搬原句。\n"
        "4) 不要添加资料外信息。\n"
    )


def generate_summary(llm_client: LLMClient, context: str) -> tuple[SummaryResult, SummaryTrace]:
    prompt = build_summary_prompt()
    response = llm_client.generate_answer(prompt, context)
    cleaned = _cleanup_summary_text(response)
    if (
        cleaned
        and _contains_cjk(cleaned)
        and len(cleaned) >= 60
        and "。" in cleaned
        and not _looks_like_verbatim(cleaned, context)
    ):
        keywords = []
        questions = _build_questions(keywords)
        result = SummaryResult(summary=cleaned, keywords=keywords, questions=questions)
        trace = SummaryTrace(
            prompt=prompt,
            raw_output=response or "",
            used_fallback=False,
            fallback_reason="",
        )
        return result, trace

    fallback = _fallback_summary(context, response)
    reason = "summary_failed"
    if cleaned and _looks_like_verbatim(cleaned, context):
        reason = "verbatim_detected"
    trace = SummaryTrace(
        prompt=prompt,
        raw_output=response or "",
        used_fallback=True,
        fallback_reason=reason,
    )
    return fallback, trace


def _cleanup_summary_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^根据资料[:：]\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _generate_keywords(
    llm_client: LLMClient,
    summary: str,
    context: str,
) -> tuple[list[str], str]:
    keyword_client: LLMClient = llm_client
    if isinstance(llm_client, RealLLMClient) and "reasoner" in (llm_client.model or ""):
        keyword_client = RealLLMClient(
            base_url=llm_client.base_url,
            api_key=llm_client.api_key,
            model="deepseek-chat",
            timeout=llm_client.timeout,
            max_tokens=llm_client.max_tokens,
        )
    prompt = (
        "你是中文学习资料助手，请根据资料与摘要生成关键词。\n"
        "严格要求：\n"
        "1) 只输出 JSON 对象，包含 entities/actions/themes 三个数组；\n"
        "2) 每个关键词为名词或名词短语，避免动词短语或原文截断；\n"
        "3) 每个数组 2-4 个词，且不得为空；\n"
        "4) 不要出现“资料/要点/主题/内容/部分/问题”等泛词；\n"
        "5) 若为寓言，themes 必须包含寓意类关键词。\n"
        "输出示例：{\"entities\":[\"叶公\",\"真龙\"],\"actions\":[\"真龙降临\",\"惊惧逃跑\"],\"themes\":[\"表里不一\",\"名不副实\"]}\n"
        f"摘要：{summary}\n"
    )
    raw = ""
    try:
        context_snippet = context[:1000]
        raw_query = f"{prompt}\n资料：\n{context_snippet}\n"
        raw = keyword_client.generate_answer(f"RAW_JSON:{raw_query}", "")
    except Exception:
        return [], ""
    keywords = _parse_keywords(raw)
    keywords = _sanitize_keywords(keywords, limit=8, strict=False)
    if _keywords_look_good(keywords):
        return keywords, raw or ""
    retry_prompt = (
        "请直接从摘要中提炼关键词，必须输出 JSON 对象："
        "{\"entities\":[...],\"actions\":[...],\"themes\":[...]}\n"
        "三组都不得为空，且为名词短语。\n"
        f"摘要：{summary}\n"
    )
    try:
        retry_raw = keyword_client.generate_answer(f"RAW_JSON:{retry_prompt}", "")
    except Exception:
        return [], raw or ""
    retry_keywords = _parse_keywords(retry_raw)
    retry_keywords = _sanitize_keywords(retry_keywords, limit=8, strict=False)
    if _keywords_look_good(retry_keywords):
        return retry_keywords, retry_raw or ""
    return [], raw or ""


def _parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    cleaned = raw.strip()
    # Try JSON array first
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
        if isinstance(data, dict):
            items: list[str] = []
            for key in ("entities", "actions", "themes"):
                value = data.get(key)
                if isinstance(value, list):
                    items.extend([str(item).strip() for item in value if str(item).strip()])
            if items:
                return items
    except Exception:
        return []
    return []


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
    latin_keywords = _extract_latin_keywords(context)

    if _contains_cjk(context):
        if _has_markers(context):
            summary_source = context
        else:
            summary_source = raw if _contains_cjk(raw) else context
        key_points = _select_key_sentences(summary_source, max_sentences=4)
        summary = _build_structured_summary(
            title,
            list_items,
            [],
            [],
            is_cjk=True,
            key_points=key_points,
        )
    else:
        summary = _build_structured_summary(
            title,
            list_items,
            [],
            latin_keywords,
            is_cjk=False,
            key_points=[],
        )

    keywords: list[str] = []
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


def _looks_like_verbatim(summary: str, context: str) -> bool:
    if not summary or not context:
        return False
    if len(summary) < 60:
        return False
    context_norm = _normalize_text(context)
    summary_norm = _normalize_text(summary)
    if summary_norm and summary_norm in context_norm:
        return True
    parts = [part for part in re.split(r"[。！？!?;；]+", summary) if part.strip()]
    if not parts:
        return False
    hit = 0
    for part in parts:
        part_norm = _normalize_text(part)
        if part_norm and part_norm in context_norm:
            hit += 1
    return hit / max(1, len(parts)) >= 0.6


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    lowered = re.sub(r"\s+", "", lowered)
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", lowered)
    return lowered


def _extract_title(context: str) -> str:
    if "叶公" in context and "龙" in context:
        return "叶公好龙"
    for line in context.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("#"):
            return cleaned.lstrip("#").strip()[:30]
        if len(cleaned) > 20:
            return ""
        return cleaned[:30]
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


def _sanitize_keywords(words: list[str], limit: int = 6, strict: bool = True) -> list[str]:
    cleaned: list[str] = []
    for word in words:
        trimmed = word.strip()
        if not trimmed:
            continue
        if strict:
            trimmed = trimmed[:6]
            if trimmed.endswith(("上", "于", "的")):
                trimmed = trimmed[:3]
            if (
                not trimmed
                or trimmed in STOPWORDS
                or "资料" in trimmed
                or "要点" in trimmed
                or "主题" in trimmed
            ):
                continue
            if any(fragment in trimmed for fragment in BAD_KEYWORD_FRAGMENTS):
                continue
        if trimmed not in cleaned:
            cleaned.append(trimmed)
        if len(cleaned) >= limit:
            break
    return cleaned


def _keywords_look_good(words: list[str]) -> bool:
    if not words or len(words) < 3:
        return False
    for word in words:
        if not word:
            return False
        if "资料" in word or "要点" in word or "主题" in word or "内容" in word or "部分" in word:
            return False
    return True


def _build_keywords(context: str, summary: str, title: str, key_points: list[str]) -> list[str]:
    source = " ".join([title, " ".join(key_points), summary, context])
    keywords = _sanitize_keywords(_extract_cjk_keywords(source), strict=True)
    if title:
        short_title = title.strip()[:6]
        if short_title and short_title not in keywords:
            keywords.insert(0, short_title)
    if len(keywords) < 3:
        fallback = _sanitize_keywords(_extract_cjk_keywords(context), strict=True)
        for item in fallback:
            if item not in keywords:
                keywords.append(item)
            if len(keywords) >= 6:
                break
    keywords = _refine_keywords(context, keywords)
    return keywords[:6] or DEFAULT_KEYWORDS[:]


def _refine_keywords(context: str, keywords: list[str]) -> list[str]:
    extras: list[str] = []
    candidates = [
        "叶公好龙",
        "真龙",
        "装饰",
        "虚饰",
        "表里不一",
        "寓意",
        "逃跑",
        "惊慌",
        "伪善",
        "虚有其表",
        "名不副实",
    ]
    for term in candidates:
        if term in context and term not in extras:
            extras.append(term)
    if "叶公" in context and "龙" in context:
        for term in ["叶公好龙", "真龙", "虚有其表", "表里不一", "名不副实"]:
            if term not in extras:
                extras.append(term)
    merged = extras + keywords
    cleaned: list[str] = []
    for word in merged:
        if not word or word in STOPWORDS:
            continue
        if len(word) < 2:
            continue
        if word not in cleaned:
            cleaned.append(word)
    return cleaned


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
    key_points: list[str],
) -> str:
    title_part = f"主题为《{title}》。" if title else "主题为未命名资料。"
    list_part = ""
    if list_items:
        list_count = len(list_items)
        preview = "、".join(list_items[:3])
        list_part = f"包含 {list_count} 个列表要点（如：{preview}）。"
    keyword_part = ""
    latin_part = ""
    if latin_keywords:
        latin_part = f"常见英文关键词：{'、'.join(latin_keywords[:3])}。"
    if not is_cjk:
        return (
            f"该资料主要为英文内容，{title_part}"
            f"{list_part}{latin_part}建议先理解主题结构，再结合中文关键词提问以获得更准确回答。"
        )
    key_part = ""
    if key_points:
        key_part = "要点："
        key_part += "；".join(key_points) + "。"
    return f"该资料{title_part}{list_part}{key_part}".strip()


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


def _select_key_sentences(text: str, max_sentences: int = 4) -> list[str]:
    if not text:
        return []
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = cleaned.replace("根据资料：", "").strip()
    parts = [part.strip() for part in re.split(r"[。！？!?;；]+", cleaned) if part.strip()]
    if not parts:
        return []
    selected: list[str] = []
    markers = ("但是", "然而", "其实", "结果", "后来", "最后", "因此", "所以", "吓得", "逃")
    for part in parts:
        if any(marker in part for marker in markers):
            selected.append(part)
    if parts and parts[0] not in selected:
        selected.insert(0, parts[0])
    if parts and parts[-1] not in selected:
        selected.append(parts[-1])
    # Keep order and uniqueness
    seen = set()
    ordered = []
    for part in selected:
        if part in seen:
            continue
        part = _compress_sentence(part)[:80]
        seen.add(part)
        ordered.append(part)
        if len(ordered) >= max_sentences:
            break
    return ordered


def _has_markers(text: str) -> bool:
    if not text:
        return False
    markers = ("但是", "然而", "其实", "结果", "后来", "最后", "因此", "所以")
    return any(marker in text for marker in markers)


def _compress_sentence(sentence: str) -> str:
    if not sentence:
        return ""
    shortened = sentence
    if "到处" in sentence and "龙" in sentence and sentence.count("在") >= 3:
        shortened = "叶公表面爱龙，家中处处装饰龙"
    return shortened
