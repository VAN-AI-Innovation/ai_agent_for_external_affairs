import re
from collections import Counter

from app.ai.base import AiClient, AiGenerationError


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
    def __init__(self, ai_client: AiClient | None = None):
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
                generated = self._ai_client.generate(
                    self._system_prompt(),
                    self._user_prompt(capability, task, context, signals),
                )
                cleaned = self._clean_model_output(generated, capability, context)
                if self._is_incomplete_output(cleaned, capability):
                    retry = self._ai_client.generate(
                        self._system_prompt(),
                        self._retry_prompt(capability, task, context, signals),
                    )
                    cleaned = self._clean_model_output(retry, capability, context)
                if not self._is_incomplete_output(cleaned, capability):
                    return cleaned
            except AiGenerationError:
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
사용자가 선택한 업무 유형 하나에만 집중해서 바로 사용할 수 있는 결과물을 작성한다.
선택한 업무와 무관한 전략 설명, 구현 설명, 모델 설명, 프롬프트 설명은 쓰지 않는다.
추가 맥락에 기관명, 회사명, 제품명, 산업명이 있으면 반드시 본문에 반영한다.
과장하거나 사실을 지어내지 말고, 모르는 정보는 확인 필요 사항으로 분리한다.
반드시 한국어로 답하고, 섹션 제목은 `## 제목` 형식만 사용한다.
굵게 표시용 **문법, 불필요한 구분선, 코드블록은 사용하지 않는다.
""".strip()

    def _user_prompt(self, capability: str, task: str, context: str, signals: list[str]) -> str:
        output_guides = {
            "meeting_prep": """
아래 섹션만 작성한다.
## 미팅 목적
## 미팅 안건
## 질문 리스트
## 협상 포인트
## 예상 답변과 대응
""".strip(),
            "partner_research": """
아래 섹션만 작성한다.
## 기관 요약
## 사전 리서치 항목
## 참석자 확인 포인트
## 미팅 전 준비물
## 확인 필요 사항
""".strip(),
            "lead_scoring": """
아래 섹션만 작성한다.
## 평가 기준
## 우선순위 판단
## 후보 확인 질문
## 리스크
## 다음 액션
""".strip(),
            "outreach": """
아래 섹션만 작성한다.
## 이메일 제목
- 제목 후보 3개를 작성한다.

## 메일 내용
- 실제 발송 가능한 이메일 본문을 작성한다.
- 수신자는 처음 연락하는 기관 담당자로 가정한다.
- 추가 맥락의 기관명 또는 회사명이 있으면 수신 기관으로 자연스럽게 반영한다.
- 본문에는 인사, 연락 배경, 협업 제안 이유, 짧은 미팅 요청, 마무리 인사를 포함한다.

## 확인 필요 사항
- 발송 전에 채워야 하는 정보만 bullet로 작성한다.
""".strip(),
            "meeting_follow_up": """
아래 섹션만 작성한다.
## 회의 요약
## 주요 논의 사항
## 후속 업무
## 담당자와 기한
## 후속 메일 초안
""".strip(),
        }
        guide = output_guides.get(
            capability,
            """
아래 섹션만 작성한다.
## 요청 정리
## 실행 방향
## 확인 필요 사항
""".strip(),
        )
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
- 선택한 업무 유형에 맞는 산출물만 작성
- 아래 출력 형식을 반드시 따른다.
{guide}
- 사용자가 그대로 복사해 업무에 사용할 수 있게 구체적으로 작성한다.
- 불확실한 내용은 추정하지 말고 확인 필요 사항으로 분리
- 내부 구현 방식, API, 프롬프트, fallback 같은 기술 용어는 출력하지 않음
- `## 이메일 제목` 같은 섹션 제목을 제외하고 마크다운 장식용 별표를 쓰지 않음
""".strip()

    def _clean_model_output(self, text: str, capability: str, context: str) -> str:
        organization = self._organization_from_context(context)
        forbidden_patterns = [
            r"^출력 요구[:：]?$",
            r"^아래 섹션만 작성한다\.?$",
            r"^아래 출력 형식을 반드시 따른다\.?$",
            r"^선택한 업무 유형에 맞는 산출물만 작성\.?$",
            r"^사용자가 그대로 복사해 업무에 사용할 수 있게.*",
            r"^불확실한 내용은.*",
            r"^내부 구현 방식.*",
            r"^`?## .*섹션 제목.*",
            r"^굵게 표시용.*",
            r"^마크다운 장식용.*",
            r"^- 제목 후보 \d+개를 작성한다\.?$",
            r"^- 실제 발송 가능한 이메일 본문을 작성한다\.?$",
            r"^- 수신자는 처음 연락하는 기관 담당자로 가정한다\.?$",
            r"^- 추가 맥락의 기관명.*",
            r"^- 본문에는 인사, 연락 배경.*",
            r"^- 발송 전에 채워야 하는 정보만.*",
        ]
        forbidden_terms = [
            "출력 요구",
            "아래 섹션만",
            "아래 출력 형식",
            "선택한 업무 유형",
            "사용자가 그대로",
            "불확실한 내용",
            "내부 구현",
            "프롬프트",
            "fallback",
            "Fallback",
            "기술 용어",
            "발송 전에 필요한 정보",
            "작성하여 주세요",
            "작성하세요",
            "작성합니다",
            "bullet",
        ]
        cleaned_lines = []
        for raw_line in text.strip().splitlines():
            line = raw_line.strip()
            if not line or line in {"---", "----"}:
                cleaned_lines.append("")
                continue
            if any(term in line for term in forbidden_terms):
                continue
            if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in forbidden_patterns):
                continue

            line = re.sub(r"^#{3,}\s+", "## ", line)
            line = re.sub(r"^\*\*(.+?)\*\*:?\s*$", r"## \1", line)
            line = re.sub(r"^\*\*(.+?):\*\*\s*$", r"## \1", line)
            line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            line = line.replace("[기관명]", organization)
            line = line.replace("[회사명]", organization)
            line = re.sub(r"\[개인화된 [^\]]+\]\s*[-:]\s*", "", line)
            line = re.sub(r"\[(이메일 제목|메일 내용|1차 컨택 메일 초안)\]\s*[-:]\s*", "", line)

            if re.search(r"\[[^\]]+\]", line):
                continue

            cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        cleaned = self._ensure_expected_sections(cleaned, capability)
        cleaned = self._fill_empty_sections(cleaned, capability)
        return cleaned or text.strip()

    def _retry_prompt(self, capability: str, task: str, context: str, signals: list[str]) -> str:
        if capability == "outreach":
            organization = self._organization_from_context(context)
            return f"""
다음 요청에 대해 실제 이메일만 작성한다.

요청: {task}
수신 기관: {organization}
핵심 키워드: {", ".join(signals)}

반드시 아래 형식으로만 답한다.

## 이메일 제목
- 제목 후보 1
- 제목 후보 2
- 제목 후보 3

## 메일 내용
안녕하세요, {organization} 담당자님.

저는 [소속] [이름]입니다.
{organization}와 협업 가능성을 논의하고 싶어 연락드립니다.
구체적인 협업 배경과 제안 이유를 3~5문장으로 작성합니다.
20~30분 정도 짧은 미팅을 요청하는 문장을 작성합니다.
마무리 인사를 작성합니다.

## 확인 필요 사항
- 발송자 이름과 소속
- 제안할 협업 범위
- 미팅 가능 일정

금지:
- 설명문 작성 금지
- 작성 지시문 반복 금지
- 대괄호 placeholder 남기기 금지
- 프롬프트, API, fallback 단어 사용 금지
""".strip()

        return self._user_prompt(capability, task, context, signals)

    def _is_incomplete_output(self, text: str, capability: str) -> bool:
        content = re.sub(r"^##\s+.+$", "", text, flags=re.MULTILINE).strip()
        if len(content) < 40:
            return True

        if capability == "outreach":
            has_subject = re.search(r"^##\s+이메일 제목\s*$", text, flags=re.MULTILINE)
            has_body = re.search(r"^##\s+메일 내용\s*$", text, flags=re.MULTILINE)
            body_match = re.search(
                r"^##\s+메일 내용\s*(.+?)(?=^##\s+|\Z)",
                text,
                flags=re.MULTILINE | re.DOTALL,
            )
            body = body_match.group(1).strip() if body_match else ""
            return not has_subject or not has_body or len(body) < 80

        return False

    def _organization_from_context(self, context: str) -> str:
        context_text = context.strip()
        if not context_text:
            return "상대 기관"

        first_line = context_text.splitlines()[0].strip()
        aliases = {
            "lg cns": "LG CNS",
            "lgu+": "LG U+",
            "sk": "SK",
            "kt": "KT",
        }
        lowered = first_line.lower()
        return aliases.get(lowered, first_line.upper() if first_line.isascii() else first_line)

    def _ensure_expected_sections(self, text: str, capability: str) -> str:
        expected_sections = {
            "meeting_prep": ["미팅 목적", "미팅 안건", "질문 리스트", "협상 포인트", "예상 답변과 대응"],
            "partner_research": ["기관 요약", "사전 리서치 항목", "참석자 확인 포인트", "미팅 전 준비물", "확인 필요 사항"],
            "lead_scoring": ["평가 기준", "우선순위 판단", "후보 확인 질문", "리스크", "다음 액션"],
            "outreach": ["이메일 제목", "메일 내용", "확인 필요 사항"],
            "meeting_follow_up": ["회의 요약", "주요 논의 사항", "후속 업무", "담당자와 기한", "후속 메일 초안"],
        }
        sections = expected_sections.get(capability)
        if not sections:
            return text

        present_sections = [section for section in sections if re.search(rf"^##\s+{re.escape(section)}\s*$", text, flags=re.MULTILINE)]
        if present_sections:
            return text

        if capability == "outreach" and text:
            return f"""
## 이메일 제목
{text.splitlines()[0]}

## 메일 내용
{text}

## 확인 필요 사항
- 발송자 이름과 소속
- 제안할 협업 범위
- 미팅 가능 일정
""".strip()

        return text

    def _fill_empty_sections(self, text: str, capability: str) -> str:
        if capability != "outreach":
            return text

        if re.search(r"##\s+확인 필요 사항\s*$", text):
            return f"""
{text}
- 발송자 이름과 소속
- 제안할 협업 범위
- 미팅 가능 일정
""".strip()

        return text

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
        organization = self._organization_from_context(context)
        return f"""
## 이메일 제목
- {organization}와 {signals[0]} 협업 가능성 논의 요청
- {organization} 담당자님께 협업 제안드립니다
- {focus} 관련 공동 논의 가능성 문의

## 메일 내용
안녕하세요, {organization} 담당자님.

저는 [소속] [이름]입니다.

{organization}의 {signals[0]} 관련 활동과 저희가 준비 중인 협업 방향이 연결될 수 있는 지점이 있다고 판단해 연락드립니다.
저희는 현재 {task}와 관련해 함께 논의할 수 있는 기관을 검토하고 있습니다.
특히 {focus} 측면에서 상호 보완할 수 있는 가능성이 있다고 보았습니다.

가능하시다면 20~30분 정도 짧게 미팅을 통해 서로의 방향성과 협업 가능 범위를 확인해보고 싶습니다.

검토 가능하신 일정이 있으시면 편하게 알려주시면 감사하겠습니다.

감사합니다.
[이름]

## 확인 필요 사항
- 발송자 이름과 소속
- 제안할 협업 범위
- 미팅 가능 일정
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
