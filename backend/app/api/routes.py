from fastapi import APIRouter, Depends, HTTPException, status
from openai import AuthenticationError, OpenAIError, RateLimitError

from app.agents.external_affairs import CAPABILITY_GUIDE, ExternalAffairsAgent
from app.api.schemas import AgentRunRequest, AgentRunResponse
from app.core.config import Settings, get_settings
from app.llm.openai_provider import OpenAILLMProvider

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/capabilities")
def capabilities() -> dict[str, str]:
    return CAPABILITY_GUIDE


def get_agent(settings: Settings = Depends(get_settings)) -> ExternalAffairsAgent:
    try:
        return ExternalAffairsAgent(OpenAILLMProvider(settings))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/agent/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    agent: ExternalAffairsAgent = Depends(get_agent),
) -> AgentRunResponse:
    try:
        result = agent.run(
            task=payload.task,
            context=payload.context,
            capability=payload.capability,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OpenAI API 인증에 실패했습니다. OPENAI_API_KEY를 확인하세요.",
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="OpenAI API 사용량 한도 또는 결제 크레딧을 확인하세요.",
        ) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM API 호출 중 오류가 발생했습니다.",
        ) from exc

    return AgentRunResponse(result=result)
