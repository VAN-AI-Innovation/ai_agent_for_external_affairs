from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.ai.provider import create_ai_client
from app.agents.chat_assistant import ChatAssistant
from app.agents.contract_document import (
    SUPPORTED_EXTENSIONS,
    ContractDocumentAgent,
    ContractTextExtractionError,
)
from app.agents.external_affairs import CAPABILITY_GUIDE, ExternalAffairsAgent
from app.api.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ContractAnalysisResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.core.config import Settings, get_settings
from app.storage.provider import create_store
from app.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/api")

MAX_CONTRACT_FILE_BYTES = 10 * 1024 * 1024
chat_assistant: ChatAssistant | None = None
store: SQLiteStore | None = None


def get_store(settings: Settings = Depends(get_settings)) -> SQLiteStore:
    global store
    if store is None:
        store = create_store(settings)
    return store


def get_chat_assistant(
    settings: Settings = Depends(get_settings),
    app_store: SQLiteStore = Depends(get_store),
) -> ChatAssistant:
    global chat_assistant
    if chat_assistant is None:
        chat_assistant = ChatAssistant(create_ai_client(settings), app_store)
    return chat_assistant


def serialize_chat_message(message) -> dict[str, str]:
    return {
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/capabilities")
def capabilities() -> dict[str, str]:
    return CAPABILITY_GUIDE


@router.post("/chat/session", response_model=ChatSessionResponse)
def create_chat_session(
    assistant: ChatAssistant = Depends(get_chat_assistant),
) -> ChatSessionResponse:
    return ChatSessionResponse(session_id=assistant.create_session())


@router.get("/chat/{session_id}/history", response_model=ChatHistoryResponse)
def chat_history(
    session_id: str,
    assistant: ChatAssistant = Depends(get_chat_assistant),
) -> ChatHistoryResponse:
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[serialize_chat_message(message) for message in assistant.history(session_id)],
    )


@router.post("/chat/message", response_model=ChatResponse)
def chat_message(
    payload: ChatRequest,
    assistant: ChatAssistant = Depends(get_chat_assistant),
) -> ChatResponse:
    session_id = payload.session_id or assistant.create_session()
    result = assistant.reply(session_id, payload.message)
    result["message"] = serialize_chat_message(result["message"])
    return ChatResponse(**result)


@router.post("/agent/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    settings: Settings = Depends(get_settings),
) -> AgentRunResponse:
    result = ExternalAffairsAgent(create_ai_client(settings)).run(
        task=payload.task,
        context=payload.context,
        capability=payload.capability,
    )

    return AgentRunResponse(result=result)


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    app_store: SQLiteStore = Depends(get_store),
) -> FeedbackResponse:
    count = app_store.save_feedback(
        target=payload.target,
        rating=payload.rating,
        capability=payload.capability,
        prompt=payload.prompt,
        result_preview=payload.result_preview,
    )
    return FeedbackResponse(status="saved", count=count)


@router.post("/contracts/analyze", response_model=ContractAnalysisResponse)
async def analyze_contract_document(
    file: UploadFile = File(...),
    review_focus: str | None = Form(default=None),
) -> ContractAnalysisResponse:
    filename = file.filename or "contract.pdf"
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF, TXT, MD, DOCX, PNG, JPG, JPEG 파일만 업로드할 수 있습니다.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비어 있는 파일은 분석할 수 없습니다.",
        )

    if len(file_bytes) > MAX_CONTRACT_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="계약서 파일 크기는 10MB 이하만 지원합니다.",
        )

    try:
        result = ContractDocumentAgent().analyze_document(file_bytes, filename, review_focus)
    except ContractTextExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ContractAnalysisResponse(filename=filename, result=result)
