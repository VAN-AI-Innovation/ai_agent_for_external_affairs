import html
import base64
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen

from app.ai.base import AiClient, AiGenerationError


RESEARCH_CAPABILITIES = {
    "meeting_prep",
    "partner_research",
    "lead_scoring",
    "outreach",
}

_CACHE: dict[str, tuple[float, "CompanyResearchResult"]] = {}
_CACHE_TTL_SECONDS = 60 * 60 * 12


@dataclass
class ResearchSource:
    title: str
    url: str
    snippet: str


@dataclass
class CompanyResearchResult:
    company: str
    sources: list[ResearchSource]

    def to_context_block(self) -> str:
        if not self.sources:
            return ""

        lines = [
            "공개 웹 리서치:",
            f"- 검색 대상: {self.company}",
        ]
        for index, source in enumerate(self.sources, start=1):
            lines.append(f"- 출처 {index}: {source.title} ({source.url})")
            lines.append(f"  요약: {source.snippet}")
        return "\n".join(lines)


class SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str]] = []
        self._current_href = ""
        self._current_text: list[str] = []
        self._is_result_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = {key: value or "" for key, value in attrs}
        href = attr_map.get("href", "")
        css_class = attr_map.get("class", "")
        if "result__a" in css_class or "/l/?" in href:
            self._current_href = href
            self._current_text = []
            self._is_result_link = True

    def handle_data(self, data: str) -> None:
        if self._is_result_link:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._is_result_link:
            return
        title = _normalize_text(" ".join(self._current_text))
        url = _clean_search_url(self._current_href)
        if title and url and url.startswith("http"):
            self.results.append((title, url))
        self._current_href = ""
        self._current_text = []
        self._is_result_link = False


class PageTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False
        self._skip_depth = 0
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        if tag == "meta":
            attr_map = {key.lower(): value or "" for key, value in attrs}
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            if name == "description" or prop == "og:description":
                self.description = _normalize_text(attr_map.get("content", ""))

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
            return
        self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False

    def snippet(self, limit: int = 420) -> str:
        text = self.description or _normalize_text(" ".join(self._text))
        return text[:limit].rstrip()


class CompanyWebResearcher:
    def __init__(self, timeout_seconds: int = 4, max_sources: int = 3) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_sources = max_sources

    def research(self, context: str | None, capability: str | None) -> CompanyResearchResult | None:
        if capability not in RESEARCH_CAPABILITIES:
            return None

        company = self._extract_company(context or "")
        if not company:
            return None

        cache_key = company.lower()
        cached = _CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

        result = CompanyResearchResult(company=company, sources=self._collect_sources(company))
        _CACHE[cache_key] = (time.time(), result)
        return result

    def _extract_company(self, context: str) -> str:
        first_lines = [line.strip() for line in context.splitlines() if line.strip()]
        if not first_lines:
            return ""

        for line in first_lines[:4]:
            match = re.search(r"(?:기관명|회사명|기업명|상대\s*기관)\s*[:：]\s*(.+)", line)
            if match:
                return self._clean_company_name(match.group(1))

        first_line = first_lines[0]
        if len(first_line) <= 40 and not any(marker in first_line for marker in ".!?。"):
            return self._clean_company_name(first_line)
        return ""

    def _clean_company_name(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip(" -,:：")
        return cleaned[:60]

    def _collect_sources(self, company: str) -> list[ResearchSource]:
        search_results = self._search(company)
        sources: list[ResearchSource] = []
        seen_domains: set[str] = set()

        for title, url in search_results:
            domain = urlparse(url).netloc.lower().removeprefix("www.")
            if not domain or domain in seen_domains:
                continue
            source = self._fetch_source(title, url)
            if source:
                sources.append(source)
                seen_domains.add(domain)
            if len(sources) >= self.max_sources:
                break

        return sources

    def _search(self, company: str) -> list[tuple[str, str]]:
        query = quote_plus(f"{company} 공식 홈페이지 사업 소개")
        body = self._request_text(f"https://duckduckgo.com/html/?q={query}")
        if body:
            parser = SearchResultParser()
            parser.feed(body)
            if parser.results:
                return parser.results[:8]

        body = self._request_text(f"https://www.bing.com/search?q={query}")
        if not body:
            return []
        return self._parse_bing_results(body)[:8]

    def _parse_bing_results(self, body: str) -> list[tuple[str, str]]:
        results: list[tuple[str, str]] = []
        for match in re.finditer(
            r'<li class="b_algo".*?<h2.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            body,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            url = _clean_bing_url(html.unescape(match.group(1)))
            title = _normalize_text(re.sub(r"<[^>]+>", " ", match.group(2)))
            if title and url.startswith("http"):
                results.append((title, url))
        return results

    def _fetch_source(self, fallback_title: str, url: str) -> ResearchSource | None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.path.lower().endswith((".pdf", ".zip", ".hwp", ".doc", ".docx", ".ppt", ".pptx")):
            return None

        body = self._request_text(url)
        if not body:
            return None

        parser = PageTextParser()
        parser.feed(body)
        title = _normalize_text(parser.title) or fallback_title
        snippet = parser.snippet()
        if len(snippet) < 40:
            snippet = fallback_title
        return ResearchSource(title=title[:120], url=url, snippet=snippet)

    def _request_text(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; VANExternalAffairsMVP/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    return ""
                raw = response.read(400_000)
                charset = response.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="ignore")
        except (HTTPError, URLError, TimeoutError, ValueError):
            return ""


class GptAssistedCompanyWebResearcher(CompanyWebResearcher):
    def __init__(
        self,
        ai_client: AiClient,
        timeout_seconds: int = 4,
        max_sources: int = 3,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds, max_sources=max_sources)
        self._ai_client = ai_client

    def research(self, context: str | None, capability: str | None) -> CompanyResearchResult | None:
        result = super().research(context, capability)
        if not result or not result.sources or not self._ai_client.is_configured:
            return result

        try:
            return self._refine_with_gpt(result, capability or "general")
        except AiGenerationError:
            return result

    def _refine_with_gpt(self, result: CompanyResearchResult, capability: str) -> CompanyResearchResult:
        source_lines = "\n".join(
            f"{index}. 제목: {source.title}\nURL: {source.url}\n요약: {source.snippet}"
            for index, source in enumerate(result.sources, start=1)
        )
        refined = self._ai_client.generate(
            """
너는 한국어 대외업무 리서치 보조자다.
제공된 공개 웹 자료 안에서만 기관 특징과 협업 관련 포인트를 정리한다.
새로운 사실, 매출, 임직원 수, 제품명, 최근 뉴스는 자료에 없으면 쓰지 않는다.
각 줄은 반드시 `제목 | URL | 요약` 형식으로만 작성한다.
""".strip(),
            f"""
업무 유형: {capability}
검색 대상: {result.company}

공개 웹 자료:
{source_lines}

요청:
- 각 출처별로 대외업무에 필요한 핵심만 1문장으로 압축한다.
- URL은 원문 그대로 유지한다.
- 형식 예: LG | https://lg.co.kr/ | 공식 홈페이지 설명을 바탕으로 협업 검토에 필요한 특징을 요약
""".strip(),
        )

        refined_sources = self._parse_refined_sources(refined, result.sources)
        if not refined_sources:
            return result
        return CompanyResearchResult(company=result.company, sources=refined_sources[: self.max_sources])

    def _parse_refined_sources(self, text: str, original_sources: list[ResearchSource]) -> list[ResearchSource]:
        known_urls = {source.url for source in original_sources}
        refined_sources: list[ResearchSource] = []
        for line in text.splitlines():
            parts = [part.strip(" -") for part in line.split("|")]
            if len(parts) < 3:
                continue
            title, url, snippet = parts[0], parts[1], " | ".join(parts[2:])
            if url not in known_urls:
                continue
            if title and snippet:
                refined_sources.append(ResearchSource(title=title[:120], url=url, snippet=snippet[:420]))
        return refined_sources


def append_company_research_context(
    context: str | None,
    capability: str | None,
    researcher: CompanyWebResearcher | None = None,
) -> str:
    base_context = (context or "").strip()
    research = (researcher or CompanyWebResearcher()).research(base_context, capability)
    research_block = research.to_context_block() if research else ""
    if not research_block:
        return base_context
    if not base_context:
        return research_block
    return f"{base_context}\n\n{research_block}"


def _clean_search_url(url: str) -> str:
    unescaped = html.unescape(url)
    parsed = urlparse(unescaped)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return query["uddg"][0]
    return unescaped


def _clean_bing_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    raw_target = query.get("u", [""])[0]
    if parsed.netloc.endswith("bing.com") and raw_target.startswith("a1"):
        encoded = raw_target[2:]
        padding = "=" * (-len(encoded) % 4)
        try:
            return base64.urlsafe_b64decode(f"{encoded}{padding}").decode("utf-8", errors="ignore")
        except ValueError:
            return url
    return url


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()
