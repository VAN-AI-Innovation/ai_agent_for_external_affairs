import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.ai.base import AiClient


TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]{2,}")
SECURITY_KEYWORDS = {
    "api key",
    "apikey",
    "password",
    "비밀번호",
    "토큰",
    "시크릿",
    "secret",
    "credential",
    "인증키",
    "내부망",
}

CASUAL_KEYWORDS = {"안녕", "고마워", "감사", "뭐해", "누구", "도움", "hello", "hi"}
BUSINESS_KEYWORDS = {
    "계약",
    "매뉴얼",
    "담당자",
    "미팅",
    "회의",
    "기관",
    "리서치",
    "컨택",
    "메일",
    "후속",
    "협력",
    "위험",
}

MANUAL_CHUNKS = [
    {
        "id": "manual-contract-01",
        "title": "계약 검토 절차",
        "text": "계약서는 계약 목적, 계약 기간, 금액, 해지 조건, 비밀유지, 손해배상, 지식재산권, 관할 조항을 우선 확인한다. 불리하거나 모호한 표현은 위험 요소로 분리하고 법무 검토가 필요한 항목은 확인 필요 사항으로 남긴다.",
    },
    {
        "id": "manual-meeting-01",
        "title": "사전 미팅 준비",
        "text": "대외 미팅 전에는 상대 기관의 주요 사업, 최근 프로젝트, 참석자 역할, 의사결정 권한, 예상 관심사를 정리한다. 미팅 안건, 질문 리스트, 협상 포인트, 예상 답변을 준비한다.",
    },
    {
        "id": "manual-contact-01",
        "title": "1차 컨택 원칙",
        "text": "처음 연락하는 기관에는 개인화된 배경, 협업 제안 이유, 상대방이 얻을 수 있는 이익, 짧은 미팅 요청, 후속 액션을 포함한다. 과도한 확정 표현은 피하고 확인 가능한 범위로 작성한다.",
    },
    {
        "id": "manual-followup-01",
        "title": "미팅 후속 정리",
        "text": "미팅 후에는 회의 요약, 주요 논의 사항, 후속 업무, 담당자, 기한, 확인 필요 사항, 후속 메일 초안을 정리한다. 담당자와 기한이 비어 있으면 확인 필요 사항으로 표시한다.",
    },
    {
        "id": "manual-risk-01",
        "title": "보안 및 민감정보 처리",
        "text": "API 키, 비밀번호, 내부 인증 정보, 고객 개인정보, 비공개 계약 조건은 챗봇 답변으로 노출하지 않는다. 민감정보 요청이 들어오면 제공을 거절하고 안전한 확인 절차를 안내한다.",
    },
]


@dataclass
class ChatMessage:
    role: str
    content: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


class ChatAssistant:
    def __init__(self, ai_client: AiClient | None = None, store=None):
        self._ai_client = ai_client
        self._store = store
        self._sessions: dict[str, list[ChatMessage]] = {}

    def create_session(self) -> str:
        session_id = uuid4().hex
        welcome_message = ChatMessage(
            role="assistant",
            content="안녕하세요. 대외업무 매뉴얼 검색, 담당자 확인 질문 정리, 미팅 준비를 도와드릴게요.",
        )
        if self._store:
            self._store.create_chat_session(session_id)
            self._store.add_chat_message(session_id, welcome_message)
        else:
            self._sessions[session_id] = [welcome_message]
        return session_id

    def history(self, session_id: str) -> list[ChatMessage]:
        if self._store:
            return self._store.get_chat_history(session_id)
        return self._sessions.setdefault(session_id, [])

    def reply(self, session_id: str, message: str) -> dict[str, object]:
        user_message = message.strip()
        user_chat_message = ChatMessage(role="user", content=user_message)
        if self._store:
            self._store.add_chat_message(session_id, user_chat_message)
        else:
            session = self._sessions.setdefault(session_id, [])
            session.append(user_chat_message)

        if self._is_blocked(user_message):
            answer = self._blocked_answer()
            references = [{"id": "manual-risk-01", "title": "보안 및 민감정보 처리"}]
            intent = "blocked"
        else:
            intent = self._classify_intent(user_message)
            matches = self._retrieve(user_message)
            references = [{"id": item["id"], "title": item["title"]} for item in matches]
            answer = self._generate_answer(user_message, intent, matches)

        assistant_message = ChatMessage(role="assistant", content=answer)
        if self._store:
            self._store.add_chat_message(session_id, assistant_message)
        else:
            session.append(assistant_message)
            self._sessions[session_id] = session[-30:]

        return {
            "session_id": session_id,
            "message": assistant_message,
            "intent": intent,
            "references": references,
        }

    def _is_blocked(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in SECURITY_KEYWORDS)

    def _classify_intent(self, text: str) -> str:
        lowered = text.lower()
        if any(keyword in lowered for keyword in BUSINESS_KEYWORDS):
            return "business"
        if len(text) <= 30 and any(keyword in lowered for keyword in CASUAL_KEYWORDS):
            return "casual"
        return "business"

    def _retrieve(self, query: str, limit: int = 3) -> list[dict[str, str]]:
        query_tokens = Counter(self._tokens(query))
        scored = []
        for chunk in MANUAL_CHUNKS:
            chunk_tokens = Counter(self._tokens(f"{chunk['title']} {chunk['text']}"))
            score = sum(min(count, chunk_tokens[token]) for token, count in query_tokens.items())
            if score:
                scored.append((score, chunk))

        if not scored:
            return MANUAL_CHUNKS[:2]

        return [chunk for _, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]

    def _tokens(self, text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]

    def _generate_answer(self, question: str, intent: str, matches: list[dict[str, str]]) -> str:
        if intent == "casual":
            return "안녕하세요. 계약 검토, 기관 리서치, 미팅 준비, 1차 컨택, 후속 정리 중 필요한 걸 물어보시면 바로 도와드릴게요."

        references = ", ".join(item["title"] for item in matches)
        return f"""
## 답변
- 질문과 가장 가까운 내부 매뉴얼 기준은 `{matches[0]["title"]}`입니다.
- {matches[0]["text"]}
- 실제 업무에 적용하기 전에는 상대 기관, 일정, 담당자, 승인 절차를 함께 확인하세요.

## 확인 필요 사항
- 질문의 대상 기관 또는 담당자가 누구인지 확인
- 현재 단계가 사전 리서치, 미팅 준비, 계약 검토, 후속 정리 중 어디인지 확인
- 내부 공유가 가능한 정보와 민감정보를 구분

## 출처
- {references}
""".strip()

    def _blocked_answer(self) -> str:
        return """
## 답변 제한
- API 키, 비밀번호, 내부 인증 정보, 비공개 보안 정보는 챗봇에서 제공할 수 없습니다.
- 필요한 경우 권한이 있는 담당자에게 공식 절차로 확인해 주세요.

## 대신 도와드릴 수 있는 것
- 보안 정보를 제외한 업무 절차 정리
- 담당자에게 보낼 확인 요청 문안 작성
- 민감정보 없이 공유 가능한 회의 메모 정리

## 출처
- 보안 및 민감정보 처리
""".strip()
