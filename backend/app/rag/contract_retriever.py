import math
import re
from dataclasses import dataclass
from typing import Iterable


TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]{2,}")

CONTRACT_REVIEW_QUERIES = {
    "계약 개요": "계약 당사자 목적 기간 효력 발생일 계약금액 대금 수수료 지급",
    "핵심 조항": "계약 기간 해지 갱신 비밀유지 지식재산권 손해배상 책임 제한 관할 준거법",
    "주요 의무사항": "의무 제공 납품 지급 보고 승인 협조 통지 기한 조건",
    "위험 요소": "위약벌 손해배상 면책 책임 제한 일방 해지 자동 갱신 지연 이자 모호 위반 금지",
    "확인 필요 사항": "별도 합의 협의 추후 정한다 명시되지 않음 예외 사전 승인 확인",
}


@dataclass(frozen=True)
class ContractChunk:
    index: int
    text: str
    tokens: set[str]


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def chunk_contract_text(text: str, max_chars: int = 3500, overlap: int = 350) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        split_at = text.rfind("\n\n", start, end)
        if split_at <= start + max_chars * 0.45:
            split_at = text.rfind("\n", start, end)
        if split_at <= start + max_chars * 0.45:
            split_at = end

        chunks.append(text[start:split_at].strip())
        if split_at >= len(text):
            break
        start = max(0, split_at - overlap)

    return [chunk for chunk in chunks if chunk]


class ContractRetriever:
    def __init__(self, chunks: Iterable[str]):
        self._chunks = [
            ContractChunk(index=index, text=text, tokens=tokenize(text))
            for index, text in enumerate(chunks, start=1)
        ]
        self._document_frequency = self._count_document_frequency()

    def retrieve(self, query: str, top_k: int = 4) -> list[ContractChunk]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return self._chunks[:top_k]

        scored = [
            (self._score(chunk, query_tokens), chunk)
            for chunk in self._chunks
        ]
        ranked = [chunk for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]
        return ranked[:top_k] or self._chunks[:top_k]

    def build_review_context(self, top_k: int = 4) -> str:
        sections = []
        for section, query in CONTRACT_REVIEW_QUERIES.items():
            chunks = self.retrieve(query, top_k=top_k)
            chunk_text = "\n\n".join(
                f"[관련 원문 {chunk.index}]\n{chunk.text}"
                for chunk in chunks
            )
            sections.append(f"### {section} 관련 검색 결과\n{chunk_text}")

        return "\n\n".join(sections)

    def _count_document_frequency(self) -> dict[str, int]:
        frequency: dict[str, int] = {}
        for chunk in self._chunks:
            for token in chunk.tokens:
                frequency[token] = frequency.get(token, 0) + 1
        return frequency

    def _score(self, chunk: ContractChunk, query_tokens: set[str]) -> float:
        score = 0.0
        total_chunks = max(len(self._chunks), 1)
        for token in query_tokens:
            if token not in chunk.tokens:
                continue
            document_frequency = self._document_frequency.get(token, 0)
            inverse_document_frequency = math.log((1 + total_chunks) / (1 + document_frequency)) + 1
            score += inverse_document_frequency
        return score
