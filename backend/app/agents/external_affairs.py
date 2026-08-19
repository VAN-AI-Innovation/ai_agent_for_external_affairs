import re
from collections import Counter

from app.ai.local_qwen import LocalModelUnavailableError, LocalQwenClient


CAPABILITY_GUIDE = {
    "contract_review": "계약서 파일 업로드 기능에서 핵심 조항, 위험 요소, 확인 필요 사항을 정리합니다.",
    "meeting_prep": "미팅 안건, 질문, 협상 포인트, 예상 답변을 작성합니다.",
    "partner_research": "상대 기관과 참석자 사전 리서치 관점을 정리합니다.",
    "lead_scoring": "협력 대상 리스트업과 적합도 평가 기준을 제안합니다.",
    "outreach": "개인화된 1차 컨택 문안을 작성합니다.",
    "meeting_follow_up": "회의록, 후속 업무, 담당자 정리 양식을 만듭니다.",
}

TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]{2,}")
STOPWORDS = {
    "그리고",
    "에서",
    "으로",
    "에게",
    "대한",
    "관련",
    "위한",
    "사용",
    "작성",
    "정리",
    "만들어줘",
    "준비해줘",
}


class ExternalAffairsAgent:
    def __init__(self, ai_client: LocalQwenClient | None = None):
        self._ai_client = ai_client

    def run(self, task: str, context: str | None = None, capability: str | None = None) -> str:
        task_text = task.strip()
        context_text = context.strip() if context else ""
        signals = self._extract_signals(f"{task_text}\n{context_text}")

        if capability == "contract_review":
            return self._contract_review_guide()
        if capability == "meeting_prep":
            return self._run_ai_or_fallback(capability, task_text, context_text, signals)
        if capability == "partner_research":
            return self._run_ai_or_fallback(capability, task_text, context_text, signals)
        if capability == "lead_scoring":
            return self._run_ai_or_fallback(capability, task_text, context_text, signals)
        if capability == "outreach":
            return self._run_ai_or_fallback(capability, task_text, context_text, signals)
        if capability == "meeting_follow_up":
            return self._run_ai_or_fallback(capability, task_text, context_text, signals)

        return self._run_ai_or_fallback(capability or "general", task_text, context_text, signals)

    def _extract_signals(self, text: str) -> list[str]:
        tokens = [
            token
            for token in TOKEN_PATTERN.findall(text)
            if token not in STOPWORDS and len(token) >= 2
        ]
        ranked = Counter(tokens).most_common(8)
        return [token for token, _ in ranked] or ["협업", "일정", "담당자"]

    def _focus(self, signals: list[str], limit: int = 4) -> str:
        return ", ".join(signals[:limit])

    def _run_ai_or_fallback(self, capability: str, task: str, context: str, signals: list[str]) -> str:
        if self._ai_client and self._ai_client.is_configured:
            try:
                return self._ai_client.generate(
                    self._system_prompt(),
                    self._user_prompt(capability, task, context, signals),
                )
            except LocalModelUnavailableError:
                pass

        return self._fallback(capability, task, context, signals)

    def _fallback(self, capability: str, task: str, context: str, signals: list[str]) -> str:
        if capability == "meeting_prep":
            return self._meeting_prep(task, context, signals)
        if capability == "partner_research":
            return self._partner_research(task, context, signals)
        if capability == "lead_scoring":
            return self._lead_scoring(task, context, signals)
        if capability == "outreach":
            return self._outreach(task, context, signals)
        if capability == "meeting_follow_up":
            return self._meeting_follow_up(task, context, signals)
        return self._general(task, context, signals)

    def _system_prompt(self) -> str:
        return """
너는 한국어 대외업무 AI 에이전트다.
사용자의 요청과 추가 맥락을 바탕으로 바로 업무에 사용할 수 있는 결과물을 작성한다.
과장하지 말고, 모르는 정보는 확인 필요 사항으로 분리한다.
반드시 한국어로 답하고, 명확한 제목과 bullet을 사용한다.
""".strip()

    def _user_prompt(self, capability: str, task: str, context: str, signals: list[str]) -> str:
        output_guides = {
            "meeting_prep": "미팅 개요, 미팅 안건, 질문 리스트, 협상 포인트, 예상 답변과 대응을 작성",
            "partner_research": "리서치 목표, 사전 리서치 항목, 참석자 확인 포인트, 미팅 전 준비물을 작성",
            "lead_scoring": "평가 목표, 평가 기준 표, 우선순위 판단 기준, 후보별 확인 질문을 작성",
            "outreach": "컨택 전략, 이메일 제목 후보, 1차 컨택 메일 초안, 후속 액션을 작성",
            "meeting_follow_up": "회의 요약, 주요 논의 사항, 후속 업무 표, 확인 필요 사항, 후속 메일 초안을 작성",
        }
        guide = output_guides.get(capability, "요청 정리, 실행 방향, 확인 필요 사항을 작성")
        return f"""
업무 유형:
{CAPABILITY_GUIDE.get(capability, "대외업무 지원")}

요청:
{task}

추가 맥락:
{context or "제공된 추가 맥락 없음"}

추출된 핵심 키워드:
{", ".join(signals)}

출력 요구:
- {guide}
- 사용자가 그대로 복사해 업무에 사용할 수 있게 구체적으로 작성
- 불확실한 내용은 추정하지 말고 확인 필요 사항으로 분리
- 내부 구현 방식, API, 프롬프트, fallback 같은 기술 용어는 출력하지 않음
""".strip()

    def _contract_review_guide(self) -> str:
        return """
## 계약 검토 안내
- 왼쪽 `계약 검토` 탭에서 계약서 파일을 선택하면 원문 기반 분석을 진행할 수 있습니다.
- 분석 결과는 계약 개요, 핵심 조항, 주요 의무사항, 위험 요소, 확인 필요 사항으로 정리됩니다.

## 권장 사용 흐름
- 계약서 파일 선택
- 분석 기준 입력
- `분석` 버튼 클릭
""".strip()

    def _meeting_prep(self, task: str, context: str, signals: list[str]) -> str:
        focus = self._focus(signals)
        return f"""
## 미팅 개요
- 목적: {task}
- 핵심 키워드: {focus}
- 참고 맥락: {context or "추가 맥락 없음"}

## 미팅 안건
- 협업 목적과 기대 성과 확인
- {signals[0]} 관련 현재 상황 공유
- 역할 분담, 일정, 의사결정 방식 합의
- 비용, 법무, 보안, 운영 리스크 확인
- 다음 액션과 담당자 확정

## 질문 리스트
- 이번 논의에서 상대방이 가장 중요하게 보는 성과 지표는 무엇인가?
- {signals[0]} 진행을 위해 상대방이 제공할 수 있는 자원은 무엇인가?
- 의사결정자는 누구이며 내부 승인 절차는 어떻게 되는가?
- 일정이 지연될 경우 조정 가능한 범위는 어디까지인가?
- 계약, 비용, 데이터, 브랜드 사용과 관련해 사전 확인이 필요한 조건은 무엇인가?

## 협상 포인트
- 우선순위: 빠른 파일럿 진행보다 역할과 책임 범위를 명확히 하는 것을 우선합니다.
- 양보 가능 항목: 일정, 회의 주기, 파일럿 범위
- 방어할 항목: 비용 부담, 책임 범위, 독점 조건, 데이터 사용 권한

## 예상 답변과 대응
- 상대방이 “내부 검토가 필요하다”고 답할 경우: 검토 기준과 회신 일정을 먼저 합의합니다.
- 상대방이 “범위를 넓히자”고 제안할 경우: 파일럿 범위와 본계약 범위를 분리합니다.
- 상대방이 “비용을 낮추자”고 요청할 경우: 제공 범위, 일정, 산출물을 함께 조정합니다.
""".strip()

    def _partner_research(self, task: str, context: str, signals: list[str]) -> str:
        focus = self._focus(signals)
        return f"""
## 리서치 목표
- 요청 내용: {task}
- 우선 확인 키워드: {focus}
- 참고 맥락: {context or "추가 맥락 없음"}

## 사전 리서치 항목
- 기관의 주요 사업, 고객군, 최근 프로젝트
- {signals[0]}와 연결되는 서비스, 제품, 연구, 제휴 사례
- 의사결정 구조와 협업 담당 부서
- 보유 채널, 데이터, 콘텐츠, 커뮤니티 등 협업 자산
- 경쟁사 또는 유사 기관과의 차별점

## 참석자 확인 포인트
- 직무와 의사결정 권한
- 최근 발표, 인터뷰, 프로젝트 이력
- 미팅에서 관심 가질 만한 성과 지표

## 리서치 질문
- 이 기관이 지금 {signals[0]} 협업을 추진할 동기가 충분한가?
- 우리 쪽 제안이 상대방의 현재 과제와 어떻게 연결되는가?
- 협업 성사에 영향을 줄 수 있는 리스크는 무엇인가?

## 미팅 전 준비물
- 기관 소개 3줄 요약
- 협업 가설 2개
- 상대방에게 확인할 질문 5개
- 제안 가능한 파일럿 범위 1개
""".strip()

    def _lead_scoring(self, task: str, context: str, signals: list[str]) -> str:
        focus = self._focus(signals)
        return f"""
## 평가 목표
- 요청 내용: {task}
- 평가 키워드: {focus}
- 참고 맥락: {context or "추가 맥락 없음"}

## 적합도 평가 기준
| 기준 | 배점 | 확인 방법 |
| --- | ---: | --- |
| 전략적 적합성 | 25 | 우리 목표와 상대방 사업 방향이 맞는지 확인 |
| 실행 가능성 | 20 | 담당자, 예산, 일정, 승인 절차 확인 |
| 시장/채널 영향력 | 20 | 고객 접점, 커뮤니티, 브랜드 신뢰도 확인 |
| 상호 이익 | 20 | 양쪽이 얻는 성과가 균형적인지 확인 |
| 리스크 | 15 | 법무, 비용, 운영, 평판 리스크 확인 |

## 우선순위 판단
- 80점 이상: 바로 미팅 또는 제안서 발송
- 60~79점: 추가 정보 확인 후 미팅 여부 결정
- 60점 미만: 단기 우선순위에서 제외

## 후보별 확인 질문
- {signals[0]} 관점에서 상대방이 가진 강점은 무엇인가?
- 협업 담당자와 의사결정자가 분리되어 있는가?
- 파일럿을 작게 시작할 수 있는가?
- 우리 쪽 리소스 대비 기대 효과가 충분한가?
""".strip()

    def _outreach(self, task: str, context: str, signals: list[str]) -> str:
        focus = self._focus(signals)
        return f"""
## 컨택 전략
- 요청 내용: {task}
- 개인화 포인트: {focus}
- 참고 맥락: {context or "추가 맥락 없음"}

## 이메일 제목 후보
- {signals[0]} 관련 협업 제안드립니다
- {signals[0]} 분야 공동 논의 가능성 문의
- 귀 기관과의 협업 가능성 검토 요청

## 1차 컨택 메일 초안
안녕하세요, 담당자님.

저는 [소속/이름]입니다. 귀 기관의 {signals[0]} 관련 활동을 확인하고, 저희가 준비 중인 협업 방향과 연결될 수 있는 지점이 있어 연락드립니다.

저희는 현재 {task}을 목표로 논의 대상을 검토하고 있습니다. 특히 {focus} 측면에서 상호 보완할 수 있는 가능성이 있다고 판단했습니다.

가능하시다면 20~30분 정도 짧게 미팅을 통해 서로의 방향성과 협업 가능 범위를 확인해보고 싶습니다.

검토 가능하신 일정이 있으시면 편하게 알려주시면 감사하겠습니다.

감사합니다.
[이름]

## 후속 액션
- 3영업일 내 미회신 시 짧은 리마인드 발송
- 회신 시 미팅 목적, 예상 안건, 참석자를 먼저 공유
- 관심이 낮을 경우 뉴스레터/자료 공유 관계로 전환
""".strip()

    def _meeting_follow_up(self, task: str, context: str, signals: list[str]) -> str:
        focus = self._focus(signals)
        return f"""
## 회의 요약
- 정리 대상: {task}
- 핵심 키워드: {focus}
- 참고 메모: {context or "추가 메모 없음"}

## 주요 논의 사항
- 협업 목적과 기대 효과
- {signals[0]} 관련 상대방 관심사
- 일정, 역할, 필요 자료
- 미확정 조건과 리스크

## 후속 업무
| 업무 | 담당자 | 기한 | 상태 |
| --- | --- | --- | --- |
| 미팅 요약본 공유 | 내부 담당자 | D+1 | 예정 |
| 상대방 확인 질문 발송 | 내부 담당자 | D+2 | 예정 |
| 제안 범위/견적/자료 정리 | 사업 담당자 | D+3 | 예정 |
| 다음 미팅 일정 조율 | 양측 담당자 | D+5 | 예정 |

## 확인 필요 사항
- 상대방의 최종 의사결정자는 누구인가?
- 다음 미팅 전까지 받아야 할 자료는 무엇인가?
- 계약 또는 비용 검토가 필요한 항목은 무엇인가?

## 후속 메일 초안
안녕하세요, 담당자님.

오늘 논의 감사드립니다. 말씀 나눈 내용을 기준으로 주요 논의 사항과 후속 확인 항목을 정리해 공유드립니다.

확인 후 수정하거나 보완할 내용이 있다면 편하게 말씀 부탁드립니다. 다음 단계 진행을 위해 필요한 자료와 일정도 함께 조율드리겠습니다.

감사합니다.
""".strip()

    def _general(self, task: str, context: str, signals: list[str]) -> str:
        return f"""
## 요청 정리
- 요청 내용: {task}
- 핵심 키워드: {self._focus(signals)}
- 참고 맥락: {context or "추가 맥락 없음"}

## 실행 방향
- 목표, 상대방, 일정, 리스크를 먼저 정리합니다.
- 필요한 자료와 의사결정자를 확인합니다.
- 다음 액션과 담당자를 지정합니다.
""".strip()
