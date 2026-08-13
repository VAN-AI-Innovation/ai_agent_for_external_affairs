# 대외업무 통합 AI 에이전트

계약서 검토부터 사전 미팅 준비, 1차 컨택, 미팅 후속 정리까지 대외업무 전반을 지원하는 AI 에이전트 프로젝트입니다.

## Day 1 범위

- FastAPI 기반 백엔드 API
- React + Vite 기반 프론트엔드
- OpenAI LLM API 연동
- `.env` 기반 환경변수 관리
- 향후 업무별 에이전트 확장을 고려한 디렉터리 구조
- 백엔드와 프론트엔드를 각각 독립 실행하거나 한 번에 실행할 수 있는 개발 스크립트

기술 선택 이유와 비교 내용은 [기술 의사결정 기록](docs/TECHNICAL_DECISIONS.md)에 정리합니다.
주차별 작업 과정은 [주차별 개발 기록](docs/WEEKLY_PROGRESS.md)에 정리합니다.
Push 단위 작업 요약은 [Push 기록](docs/PUSH_LOG.md)에 정리합니다.

## 프로젝트 구조

```text
.
├── backend/
│   ├── app/
│   │   ├── agents/       # 대외업무 에이전트 로직
│   │   ├── api/          # API 라우터와 스키마
│   │   ├── core/         # 설정, 공통 구성
│   │   └── llm/          # LLM provider 추상화와 구현체
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
├── scripts/              # 개발 서버 실행 스크립트
├── docs/                 # 기술 의사결정 기록
├── .env.example
└── package.json
```

## 구조 설계 메모

초기 개발에서는 백엔드와 프론트엔드를 분리해 각각 독립적인 서버로 실행하도록 구성했습니다. 백엔드는 API 요청 처리, Agent 실행, LLM API 호출을 담당하고, 프론트엔드는 사용자가 업무 유형을 선택하고 요청 결과를 확인하는 화면을 담당합니다. 이렇게 역할을 나누면 문제가 발생했을 때 API 문제인지 UI 문제인지 구분하기 쉽고, 추후 계약서 검토, 미팅 준비, 컨택 문안 작성 같은 기능을 각각 확장하기도 수월합니다.

다만 개발할 때마다 터미널을 두 개 열어 백엔드와 프론트엔드를 따로 실행하는 것은 번거롭기 때문에, 루트에서 `npm run dev` 한 번으로 두 서버가 함께 실행되도록 했습니다. 즉, 내부 구조는 분리해 유지보수성을 확보하고, 실행 경험은 단순하게 만들어 개발 효율을 높이는 방향으로 구성했습니다.

LLM 연동도 같은 이유로 Agent 코드와 OpenAI 호출 코드를 분리했습니다. 현재는 OpenAI 단일 모델을 사용하지만, 나중에 모델을 교체하거나 다른 LLM API를 비교해야 할 때 수정 범위를 줄이기 위해 `LLMProvider` 구조를 먼저 잡아두었습니다.

## 기술적으로 고민한 지점

이 프로젝트는 단순히 LLM API를 한 번 호출하는 예제에서 끝나지 않고, 실제 대외업무 흐름을 여러 기능으로 확장하는 것을 전제로 설계했습니다. 그래서 Day 1 단계에서도 아래 기준을 두고 구조를 잡았습니다.

- **역할 분리**: API 라우터는 HTTP 요청과 응답만 담당하고, 업무 로직은 Agent 모듈로 분리했습니다. 이후 계약서 검토, 미팅 준비, 컨택 문안 작성처럼 서로 다른 업무 흐름이 추가되어도 라우터가 비대해지는 것을 줄이기 위한 선택입니다.
- **모델 교체 가능성**: OpenAI SDK 호출을 Agent 내부에 직접 넣지 않고 `LLMProvider`로 한 번 감쌌습니다. 현재는 OpenAI 단일 모델을 사용하지만, 추후 다른 모델을 테스트하거나 비용/성능 비교를 할 때 provider 구현체만 바꾸면 되도록 했습니다.
- **보안 기본값**: API Key는 `.env`에만 저장하고, Git에는 `.env.example`만 포함했습니다. 개발 초기부터 민감정보가 저장소에 섞이지 않도록 관리하는 것을 기본 전제로 두었습니다.
- **개발 편의성과 디버깅 균형**: 프론트엔드와 백엔드는 각각 독립 실행할 수 있게 두면서도, 루트에서는 `npm run dev` 한 줄로 동시에 켤 수 있게 했습니다. 독립 실행은 문제 원인 추적에 유리하고, 동시 실행은 반복 개발 속도를 높입니다.
- **실패 상황 처리**: OpenAI API 호출에서 인증 실패, 사용량 한도 초과, 일반 API 오류를 구분해 처리했습니다. 실제 테스트 중 개인 결제 크레딧 부족으로 `credit_balance_exhausted`가 발생했고, 이를 사용자에게 이해 가능한 메시지로 반환하도록 정리했습니다.
- **기록 기반 개발**: 기술 선택 이유와 비교 내용은 `docs/TECHNICAL_DECISIONS.md`, 주차별 작업 과정은 `docs/WEEKLY_PROGRESS.md`에 따로 기록했습니다. 기능을 추가할 때마다 “왜 이렇게 구현했는지”를 남겨 포트폴리오에서 개발 과정과 판단 근거가 보이도록 하기 위한 목적입니다.

## 실행 준비

```bash
cp .env.example .env
```

`.env`에 실제 API Key를 입력합니다.

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

민감정보가 담긴 `.env` 파일은 `.gitignore`에 포함되어 GitHub에 올라가지 않습니다.

## 설치

Windows PowerShell 기준:

```bash
npm run install:all
```

수동 설치:

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
npm install --prefix frontend
npm install
```

## 실행

### 한 번에 실행

루트 디렉터리에서 아래 명령을 실행하면 백엔드와 프론트엔드가 동시에 켜집니다.

```bash
npm run dev
```

실행 주소:

- 프론트엔드: http://127.0.0.1:5173
- 백엔드 API: http://127.0.0.1:8000
- API 문서: http://127.0.0.1:8000/docs

### 각각 실행

백엔드만 실행:

```bash
npm run dev:backend
```

프론트엔드만 실행:

```bash
npm run dev:frontend
```

브라우저 열기:

```bash
npm run open
```

## API 테스트

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

LLM 요청:

```bash
curl -X POST http://127.0.0.1:8000/api/agent/run \
  -H "Content-Type: application/json" \
  -d "{\"task\":\"공동 마케팅 제휴 미팅 안건을 정리해줘\",\"capability\":\"meeting_prep\"}"
```

## 확장 예정 기능

- 계약서 핵심 조항, 위험 요소, 확인 필요 사항 정리
- 상대 기관과 참석자 사전 리서치
- 미팅 안건, 질문, 협상 포인트, 예상 답변 작성
- 협력 대상 리스트업과 적합도 평가
- 개인화된 1차 컨택 문안 작성
- 미팅 후 회의록, 후속 업무, 담당자 자동 정리
