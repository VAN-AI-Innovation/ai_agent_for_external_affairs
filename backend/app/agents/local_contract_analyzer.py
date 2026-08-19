import math
import re
from collections import Counter
from dataclasses import dataclass

from app.rag.contract_retriever import ContractRetriever, chunk_contract_text, tokenize


SENTENCE_PATTERN = re.compile(r"(?<=[.!?다요음함됨임됨)])\s+|\n+")

SECTION_QUERIES = {
    "계약 개요": "계약 당사자 목적 기간 금액 대금 지급 효력",
    "핵심 조항": "계약 기간 해지 갱신 비밀유지 지식재산권 손해배상 관할 준거법",
    "주요 의무사항": "의무 지급 제공 납품 보고 통지 협조 승인 검수 기한",
    "위험 요소": "손해배상 위약벌 책임 제한 일방 해지 자동 갱신 지연 모호 협의",
    "확인 필요 사항": "확인 협의 별도 합의 추후 정한다 명시 예외 승인",
}

CLAUSE_KEYWORDS = {
    "계약 기간": ["기간", "효력", "만료", "갱신", "시작일", "종료일"],
    "대금 및 지급": ["대금", "금액", "수수료", "지급", "청구", "세금계산서", "지연이자"],
    "해지": ["해지", "종료", "위반", "시정", "통지"],
    "비밀유지": ["비밀", "기밀", "정보", "누설", "보안"],
    "손해배상": ["손해배상", "배상", "책임", "위약벌", "면책"],
    "지식재산권": ["지식재산", "저작권", "소유권", "라이선스", "산출물"],
    "분쟁 해결": ["관할", "준거법", "분쟁", "소송", "중재"],
}

RISK_RULES = [
    ("높음", "손해배상/위약벌", ["손해배상", "위약벌", "배상", "책임"], "배상 범위와 책임 한도가 과도하거나 불명확할 수 있습니다."),
    ("높음", "일방 해지", ["일방", "즉시 해지", "해지할 수 있다"], "상대방에게 일방적 해지권이 넓게 부여되어 있을 수 있습니다."),
    ("중간", "자동 갱신", ["자동 갱신", "갱신"], "갱신 거절 절차를 놓치면 원치 않는 계약 연장이 발생할 수 있습니다."),
    ("중간", "모호한 협의 조항", ["협의", "추후", "별도 합의", "상호 합의"], "핵심 조건이 확정되지 않아 분쟁 가능성이 있습니다."),
    ("중간", "비밀유지", ["비밀", "기밀", "누설"], "비밀유지 기간, 예외, 반환/폐기 절차가 명확한지 확인해야 합니다."),
    ("낮음", "통지/승인 절차", ["통지", "승인", "사전 서면"], "절차를 지키지 않으면 권리 행사나 의무 이행에 문제가 생길 수 있습니다."),
]

OBLIGATION_KEYWORDS = ["하여야", "해야", "의무", "지급", "제공", "제출", "통지", "협조", "준수", "반환", "폐기"]


@dataclass(frozen=True)
class ScoredSentence:
    text: str
    score: float


def split_sentences(text: str) -> list[str]:
    sentences = [re.sub(r"\s+", " ", item).strip() for item in SENTENCE_PATTERN.split(text)]
    return [sentence for sentence in sentences if len(sentence) >= 12]


def compact(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."


class LocalContractAnalyzer:
    def analyze(self, contract_text: str, filename: str, page_count: int, review_focus: str | None = None) -> str:
        chunks = chunk_contract_text(contract_text)
        retriever = ContractRetriever(chunks)
        sentences = split_sentences(contract_text)
        scored = self._score_sentences(sentences)

        overview = self._build_overview(scored, retriever, filename, page_count, review_focus)
        clauses = self._build_clauses(sentences, retriever)
        obligations = self._build_obligations(sentences)
        risks = self._build_risks(sentences, retriever)
        questions = self._build_questions(risks, clauses, review_focus)

        return "\n\n".join([overview, clauses, obligations, risks, questions])

    def _score_sentences(self, sentences: list[str]) -> list[ScoredSentence]:
        tokenized = [tokenize(sentence) for sentence in sentences]
        document_frequency = Counter(token for tokens in tokenized for token in tokens)
        total_sentences = max(len(sentences), 1)

        scored: list[ScoredSentence] = []
        for sentence, tokens in zip(sentences, tokenized):
            if not tokens:
                continue
            score = 0.0
            for token in tokens:
                score += math.log((1 + total_sentences) / (1 + document_frequency[token])) + 1
            score += self._keyword_bonus(sentence)
            scored.append(ScoredSentence(sentence, score / math.sqrt(len(tokens))))

        return sorted(scored, key=lambda item: item.score, reverse=True)

    def _keyword_bonus(self, sentence: str) -> float:
        bonus = 0.0
        for keyword_list in CLAUSE_KEYWORDS.values():
            bonus += sum(1.3 for keyword in keyword_list if keyword in sentence)
        bonus += sum(1.8 for keyword in OBLIGATION_KEYWORDS if keyword in sentence)
        for _, _, keywords, _ in RISK_RULES:
            bonus += sum(2.0 for keyword in keywords if keyword in sentence)
        return bonus

    def _build_overview(
        self,
        scored: list[ScoredSentence],
        retriever: ContractRetriever,
        filename: str,
        page_count: int,
        review_focus: str | None,
    ) -> str:
        overview_chunks = retriever.retrieve(SECTION_QUERIES["계약 개요"], top_k=2)
        summary_sentences = [item.text for item in scored[:3]]
        source_hint = compact(overview_chunks[0].text if overview_chunks else (summary_sentences[0] if summary_sentences else ""))

        lines = [
            "## 계약 개요",
            f"- 파일명: {filename}",
            f"- 페이지 수: {page_count}",
            f"- 분석 기준: {review_focus or '별도 기준 없음'}",
            f"- 핵심 맥락: {source_hint or '계약 개요를 특정하기 위한 문장이 부족합니다.'}",
            "- 전체 요약:",
        ]
        lines.extend(f"  - {compact(sentence)}" for sentence in summary_sentences[:3])
        if not summary_sentences:
            lines.append("  - 추출된 텍스트가 짧아 요약할 문장이 부족합니다.")
        return "\n".join(lines)

    def _build_clauses(self, sentences: list[str], retriever: ContractRetriever) -> str:
        lines = ["## 핵심 조항"]
        found = False
        for clause_name, keywords in CLAUSE_KEYWORDS.items():
            candidates = self._find_sentences(sentences, keywords, limit=2)
            if not candidates:
                retrieved = retriever.retrieve(f"{clause_name} {' '.join(keywords)}", top_k=1)
                candidates = [retrieved[0].text] if retrieved else []
            if not candidates:
                continue
            found = True
            lines.append(f"- 조항명: {clause_name}")
            lines.append(f"  - 내용: {compact(candidates[0])}")
            lines.append(f"  - 검토 포인트: {self._clause_review_point(clause_name)}")

        if not found:
            lines.append("- 계약서에서 핵심 조항 후보를 충분히 찾지 못했습니다. 원문 품질 또는 PDF 텍스트 추출 상태를 확인해야 합니다.")
        return "\n".join(lines)

    def _build_obligations(self, sentences: list[str]) -> str:
        obligations = self._find_sentences(sentences, OBLIGATION_KEYWORDS, limit=6)
        lines = ["## 주요 의무사항"]
        if not obligations:
            return "\n".join(lines + ["- 명시적인 의무 표현을 충분히 찾지 못했습니다. '하여야 한다', '지급', '제공', '통지' 등 표현을 원문에서 확인해야 합니다."])

        for sentence in obligations:
            party = "우리 회사/상대방"
            if "갑" in sentence and "을" not in sentence:
                party = "갑"
            elif "을" in sentence and "갑" not in sentence:
                party = "을"
            lines.append(f"- 당사자: {party}")
            lines.append(f"  - 의무: {compact(sentence)}")
            lines.append("  - 기한/조건: 원문 조항의 날짜, 통지 기간, 지급 조건을 함께 확인")
        return "\n".join(lines)

    def _build_risks(self, sentences: list[str], retriever: ContractRetriever) -> str:
        lines = ["## 위험 요소"]
        found = False
        for level, title, keywords, description in RISK_RULES:
            candidates = self._find_sentences(sentences, keywords, limit=1)
            if not candidates:
                retrieved = retriever.retrieve(f"{title} {' '.join(keywords)}", top_k=1)
                candidates = [retrieved[0].text] if retrieved else []
            if not candidates:
                continue
            found = True
            lines.append(f"- 위험 수준: {level}")
            lines.append(f"  - 관련 조항: {title}")
            lines.append(f"  - 위험 내용: {description}")
            lines.append(f"  - 원문 근거: {compact(candidates[0])}")
            lines.append("  - 확인 또는 협상 포인트: 범위, 예외, 한도, 통지 절차를 계약서에 명확히 적는 것이 좋습니다.")

        if not found:
            lines.append("- 명확한 위험 키워드는 적게 탐지되었습니다. 다만 계약 금액, 해지, 손해배상, 비밀유지 조항은 별도 확인이 필요합니다.")
        return "\n".join(lines)

    def _build_questions(self, risks: str, clauses: str, review_focus: str | None) -> str:
        lines = ["## 확인 필요 사항"]
        if review_focus:
            lines.append(f"- 질문: 분석 기준 '{review_focus}'에 직접 연결되는 조항이 충분히 명시되어 있는가?")
            lines.append("  - 확인 대상: 사업 담당자/법무 담당자")
            lines.append("  - 이유: 사용자가 지정한 검토 관점과 계약 조항 사이의 불일치를 줄이기 위함입니다.")

        default_questions = [
            ("계약 당사자, 서명권자, 계약 효력 발생일이 명확한가?", "사업 담당자/상대방", "계약 효력과 책임 주체 확인이 필요합니다."),
            ("손해배상 책임 한도와 예외가 명확한가?", "법무 담당자", "과도한 책임 부담을 피하기 위함입니다."),
            ("해지 사유, 통지 기간, 해지 후 존속 의무가 명확한가?", "법무 담당자/사업 담당자", "중도 종료나 분쟁 상황에 대비해야 합니다."),
            ("지급 조건, 검수 기준, 산출물 범위가 구체적인가?", "사업 담당자/재무 담당자", "추가 업무와 대금 분쟁 가능성을 줄이기 위함입니다."),
        ]
        for question, owner, reason in default_questions:
            lines.append(f"- 질문: {question}")
            lines.append(f"  - 확인 대상: {owner}")
            lines.append(f"  - 이유: {reason}")
        return "\n".join(lines)

    def _find_sentences(self, sentences: list[str], keywords: list[str], limit: int) -> list[str]:
        candidates = [
            sentence
            for sentence in sentences
            if any(keyword in sentence for keyword in keywords)
        ]
        candidates.sort(key=lambda sentence: sum(sentence.count(keyword) for keyword in keywords), reverse=True)
        return candidates[:limit]

    def _clause_review_point(self, clause_name: str) -> str:
        points = {
            "계약 기간": "시작일, 종료일, 자동 갱신, 갱신 거절 통지 기한을 확인합니다.",
            "대금 및 지급": "지급 금액, 지급일, 세금계산서, 지연 이자, 지급 보류 조건을 확인합니다.",
            "해지": "일방 해지권, 시정 기간, 해지 통지 방식, 해지 후 의무를 확인합니다.",
            "비밀유지": "비밀정보 범위, 예외, 보관 기간, 반환/폐기 절차를 확인합니다.",
            "손해배상": "책임 한도, 간접손해 포함 여부, 면책 사유를 확인합니다.",
            "지식재산권": "산출물 소유권, 기존 IP 사용권, 2차 활용 가능 여부를 확인합니다.",
            "분쟁 해결": "준거법, 관할 법원, 중재 여부가 우리 회사에 불리하지 않은지 확인합니다.",
        }
        return points.get(clause_name, "조항의 적용 범위와 예외를 확인합니다.")
