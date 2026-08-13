# 주차별 개발 기록

이 문서는 주차별로 어떤 작업을 했고, 각 작업을 어떤 방식으로 구현했는지 정리합니다.

README는 프로젝트 실행 방법과 전체 소개를 중심으로 두고, 이 문서는 포트폴리오에서 개발 과정을 설명하기 위한 기록으로 사용합니다.

## 1주차: 초기 환경 구성

### 목표

대외업무 통합 AI 에이전트 개발을 시작하기 위한 기본 프로젝트 구조와 LLM API 연동 환경을 구성한다.

### 작업 내용

| 항목 | 어떻게 구현했는가 | 확인 결과 |
| --- | --- | --- |
| 프로젝트 디렉터리 구조 구성 | `backend`, `frontend`, `docs`, `scripts`로 역할을 분리했다. 백엔드는 API/Agent/LLM/설정 모듈로 나누고, 프론트엔드는 React 화면을 담당하도록 구성했다. | 기능이 늘어나도 계약서 검토, 미팅 준비, 컨택 문안 작성 등을 모듈 단위로 추가할 수 있는 구조가 됐다. |
| Python 실행 환경 및 의존성 설정 | 프로젝트 루트에 `.venv`를 생성하고, `backend/requirements.txt`에 FastAPI, Uvicorn, OpenAI SDK, pydantic-settings, python-dotenv를 명시했다. | 가상환경 기준으로 백엔드 실행과 Python 컴파일을 확인했다. |
| LLM API 연동 | OpenAI API를 사용했다. `backend/app/llm/base.py`에 `LLMProvider` 인터페이스를 만들고, `backend/app/llm/openai_provider.py`에서 OpenAI SDK의 Responses API를 호출하도록 구현했다. | API 키 로딩과 OpenAI API 호출 경로는 확인했다. 다만 개인 결제 크레딧을 사용하지 않기 위해 실제 생성 응답은 OpenAI의 `credit_balance_exhausted` 응답 단계에서 중단됐다. |
| 환경변수 관리 | `.env.example`에는 필요한 환경변수 이름과 예시 값만 작성했다. 실제 API Key는 `.env`에만 저장하고, `.gitignore`에 `.env`와 `.env.*`를 추가했다. | `git check-ignore .env`로 `.env`가 Git 추적 대상에서 제외되는 것을 확인했다. |
| 기본 API 구성 | FastAPI로 `/api/health`, `/api/capabilities`, `/api/agent/run` 엔드포인트를 만들었다. | `/api/health`가 정상 응답하는 것을 확인했다. |
| Agent 실행 구조 구성 | `ExternalAffairsAgent` 클래스를 만들고, 업무 유형을 `contract_review`, `meeting_prep`, `partner_research`, `lead_scoring`, `outreach`, `meeting_follow_up`으로 나눴다. | 현재는 단일 Agent에서 capability를 선택하는 방식이며, 추후 기능별 Agent로 분리할 수 있다. |
| React 프론트엔드 구성 | React + Vite로 간단한 테스트 UI를 만들었다. 사용자가 업무 유형을 선택하고 요청/맥락을 입력하면 백엔드 API로 전달되도록 구현했다. | 로컬 브라우저에서 `http://127.0.0.1:5173` 접속을 확인했다. |
| 개발 서버 실행 방식 구성 | `scripts/dev-backend.ps1`, `scripts/dev-frontend.ps1`, `scripts/open-app.ps1`을 추가했다. 루트 `package.json`에는 `npm run dev`, `npm run dev:backend`, `npm run dev:frontend`, `npm run open`을 등록했다. | 백엔드와 프론트엔드를 각각 실행하거나, 루트에서 한 번에 실행할 수 있게 됐다. |
| README 기본 작성 | 프로젝트 개요, 설치 방법, 실행 방법, API 테스트 방법, 확장 예정 기능을 README에 정리했다. | 처음 프로젝트를 보는 사람이 로컬 실행 흐름을 따라갈 수 있게 됐다. |

### 완료 조건 점검

| 완료 조건 | 상태 | 설명 |
| --- | --- | --- |
| 로컬 환경에서 프로젝트가 정상 실행될 것 | 완료 | 프론트엔드 `5173`, 백엔드 `8000` 포트에서 정상 실행을 확인했다. |
| 테스트 요청에 대해 LLM 응답을 받을 수 있을 것 | 부분 완료 | OpenAI API 호출 경로는 정상 확인했다. 실제 답변 생성은 API 크레딧 부족으로 중단됐다. 기업과제에서 개인 결제를 사용하지 않기 위해 이 상태를 기록한다. |
| API Key 등의 민감 정보가 GitHub에 포함되지 않을 것 | 완료 | `.env`는 `.gitignore`에 포함했고, `.env.example`에는 실제 키를 넣지 않았다. |

### 주요 의사결정

- 백엔드는 FastAPI를 선택했다. API 문서화와 요청/응답 검증이 쉽고, 향후 기능별 라우터를 분리하기 좋기 때문이다.
- 프론트엔드는 React + Vite를 선택했다. 향후 계약서 업로드, 리스크 테이블, 미팅 준비 화면, 컨택 문안 편집 등 복잡한 UI로 확장하기 좋기 때문이다.
- LLM 호출 코드는 Agent 내부에 직접 넣지 않고 provider로 분리했다. 나중에 모델이나 API 제공자를 바꿀 때 수정 범위를 줄이기 위해서다.
- 실행 방식은 각각 실행과 동시 실행을 모두 지원하도록 했다. 디버깅할 때는 백엔드/프론트를 따로 보고, 일반 개발 때는 `npm run dev` 한 줄로 켤 수 있게 하기 위해서다.

### 발생한 문제와 해결

| 문제 | 원인 | 해결 |
| --- | --- | --- |
| `.env`에서 API Key를 읽지 못함 | PowerShell로 저장된 `.env`에 BOM 문자가 포함되어 `OPENAI_API_KEY` 이름이 다르게 읽혔다. | `.env`를 UTF-8 no BOM 형식으로 다시 저장하고, 백엔드 설정이 루트 `.env`를 읽도록 수정했다. |
| OpenAI 호출 시 잘못된 키로 인식됨 | `.env`가 줄바꿈 없이 저장되어 API Key 뒤에 다른 환경변수 값이 붙었다. | `.env`를 정상적인 4줄 형식으로 다시 저장했다. |
| LLM 응답 생성 실패 | OpenAI 계정에 사용 가능한 API 크레딧이 없었다. | 코드 오류가 아니라 결제/크레딧 문제로 기록하고, 백엔드에서 429 에러 메시지를 명확히 반환하도록 처리했다. |
| 프론트 개발 서버 관련 npm audit 경고 | Vite 5 계열의 개발 서버 보안 advisory가 감지됐다. | Node 18을 지원하는 `vite@6.4.3`으로 올려 audit 0 vulnerabilities 상태를 만들었다. |

### 다음 주차 후보

- 계약서 검토 기능의 입력/출력 형식 설계
- 파일 업로드 방식 검토
- Agent 프롬프트 버전 관리 방식 정리
- LLM 응답 품질 평가 기준 작성
- DB 저장 필요 여부 검토
