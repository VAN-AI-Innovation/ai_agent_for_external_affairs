# Push 기록

공동 작업 저장소에 push할 때마다 어떤 작업을 반영했는지 간단히 기록합니다.

## 2026-08-14

### Push 대상

- Repository: `https://github.com/VAN-AI-Innovation/ai_agent_for_external_affairs.git`
- Branch: `main`

### 작업 요약

- 대외업무 통합 AI 에이전트 Day 1 초기 환경 구성
- FastAPI 백엔드 기본 API 구성
- React + Vite 프론트엔드 테스트 화면 구성
- OpenAI LLM API 연동 구조 구성
- `.env`, `.env.example`, `.gitignore` 기반 환경변수 관리
- Agent와 LLM provider 분리 구조 구성
- 백엔드/프론트 각각 실행 및 `npm run dev` 동시 실행 스크립트 추가
- README, 기술 의사결정 기록, 주차별 개발 기록 작성
- 전체 UI 색상 무채색 계열로 정리

### 확인한 내용

- `.env`는 Git 추적 대상에서 제외됨
- API Key 패턴이 커밋 대상 파일에 포함되지 않음
- 프론트엔드 빌드 통과
- 백엔드 Python 컴파일 통과
- 로컬 프론트엔드와 백엔드 실행 확인

## 2026-08-23

### Push 대상

- Repository: `https://github.com/VAN-AI-Innovation/ai_agent_for_external_affairs.git`
- Branch: `main`

### 작업 요약

- 결과 복사 버튼을 추가해 AI 산출물을 바로 다른 업무 도구에 붙여 넣을 수 있도록 개선
- 좋아요/싫어요 피드백 버튼과 `/api/feedback` 메모리 기반 수집 API 추가
- 최근 실행 기록 패널을 추가하고 브라우저 `localStorage`에 최근 결과를 저장하도록 구현
- 결과 영역 상단에 복사/피드백 액션 툴바 추가
- README에 사용성 개선 기능, 선택 이유, 개발 기록 관리 방식을 추가

### 선택 이유

- DB, 벡터 DB, 스트리밍처럼 인프라 부담이 큰 기능보다 시연 화면에서 바로 체감되는 기능을 우선 구현
- 1차 컨택 메일, 회의록, 계약서 분석 결과처럼 실제 산출물이 있는 기능은 복사와 재확인 흐름이 있을 때 업무 도구처럼 보임
- 피드백 수집은 현재는 메모리 기반이지만, 추후 DB 저장과 모델 개선 데이터로 확장 가능한 구조를 먼저 마련
- Push 기록을 함께 남겨 GitHub 커밋 히스토리와 문서 기록이 함께 포트폴리오 설명 자료가 되도록 구성

### 확인한 내용

- `python -m compileall backend/app` 통과
- `npm run build --prefix frontend` 통과
- `/api/feedback` 테스트 요청에서 `200` 응답 확인

### 추가 Push: MVP 기능 테스트 증적

- README에 `MVP 기능 테스트` 섹션 추가
- 계약서 분석 API를 텍스트 기반 샘플 계약서로 검증
- 챗봇 세션 생성, 메시지 전송, 업무 질문 분류, reference 반환 확인
- `/api/feedback` 좋아요 피드백 저장 응답 확인
- 기관 리서치, 미팅 준비, 협력 평가, 1차 컨택, 후속 정리 fallback 산출물 생성 확인
- 백엔드 컴파일과 프론트엔드 빌드 통과 결과를 README에 기록

## 2026-08-31

### Push 대상

- Repository: `https://github.com/VAN-AI-Innovation/ai_agent_for_external_affairs.git`
- Branch: `main`

### 작업 요약

- `AiClient` 공통 인터페이스를 추가해 일반 대외업무 생성 모델을 교체 가능한 구조로 분리
- `OpenAIClient`, `GeminiClient`, `LocalQwenClient`를 같은 `generate(system_prompt, user_prompt)` 방식으로 사용할 수 있게 구성
- `AI_PROVIDER=auto`에서 OpenAI API Key, Gemini API Key, Qwen 로컬 모델 순서로 provider를 선택하도록 구현
- Qwen 로컬 모델의 CPU 실행 기준 첫 요청과 두 번째 요청 처리 시간을 측정해 README에 기록
- Gemini API 전환 시 관리할 응답 시간과 구조화 출력 안정성 기준을 README에 정리
- 챗봇 세션, 챗봇 메시지, 좋아요/싫어요 피드백을 SQLite에 저장하도록 변경
- `backend/app/storage` 레이어를 추가해 추후 PostgreSQL/MySQL 같은 DB로 교체할 수 있는 진입점 마련
- 실제 DB 파일이 생성되는 `data/` 폴더를 `.gitignore`에 추가

### 선택 이유

- 현재는 Qwen 로컬 모델을 유지하되, API Key를 넣는 순간 외부 API가 같은 업무 생성 역할을 대체할 수 있게 구성
- Gemini API 전환을 앞두고 업무 로직과 모델 호출 로직을 분리해 모델 교체 시 수정 범위를 줄임
- SQLite는 별도 서버 설치 없이 사용할 수 있으면서 서버 재시작 후에도 챗봇 히스토리와 피드백이 남기 때문에 MVP 저장소로 적합
- 저장소 접근을 `storage` 레이어로 분리해 향후 DB 교체를 라우터나 Agent 수정 없이 진행하기 쉬운 구조로 만듦

### 확인한 내용

- `python -m compileall backend/app` 통과
- `npm run build --prefix frontend` 통과
- AI provider 분기 테스트 통과: Qwen, OpenAI, Gemini 선택 확인
- 챗봇 세션 생성, 메시지 전송, 히스토리 조회가 SQLite 기준으로 정상 동작 확인
- `/api/feedback` 요청이 SQLite 저장 후 `saved` 상태를 반환하는 것 확인
