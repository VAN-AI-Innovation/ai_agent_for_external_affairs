from app.llm.base import LLMProvider


SYSTEM_PROMPT = """
You are an AI assistant for external affairs work.
Help Korean business users prepare concise, practical outputs for contracts,
partner research, meetings, outreach, and follow-up tasks.

Respond in Korean unless the user explicitly requests another language.
Structure the answer with clear headings and actionable bullet points.
When information is missing, list assumptions and confirmation questions.
""".strip()


CAPABILITY_GUIDE = {
    "contract_review": "계약서 핵심 조항, 위험 요소, 확인 필요 사항을 정리합니다.",
    "meeting_prep": "미팅 안건, 질문, 협상 포인트, 예상 답변을 작성합니다.",
    "partner_research": "상대 기관과 참석자 사전 리서치 관점을 정리합니다.",
    "lead_scoring": "협력 대상 적합도 평가 기준과 우선순위를 제안합니다.",
    "outreach": "개인화된 1차 컨택 문안을 작성합니다.",
    "meeting_follow_up": "회의록, 후속 업무, 담당자 정리 양식을 만듭니다.",
}


class ExternalAffairsAgent:
    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def run(self, task: str, context: str | None = None, capability: str | None = None) -> str:
        capability_hint = CAPABILITY_GUIDE.get(capability or "", "대외업무 전반을 지원합니다.")
        user_prompt = f"""
요청 업무:
{task}

업무 유형:
{capability_hint}

참고 맥락:
{context or "제공된 추가 맥락 없음"}

출력 요구:
- 바로 실무에 옮길 수 있게 작성
- 불확실한 정보는 단정하지 말고 확인 필요 항목으로 분리
- 다음 단계 제안 포함
""".strip()

        return self._llm.generate(SYSTEM_PROMPT, user_prompt)
