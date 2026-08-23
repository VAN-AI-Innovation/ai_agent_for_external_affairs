from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    task: str = Field(..., min_length=1, description="User request for the agent")
    context: str | None = Field(default=None, description="Optional business context")
    capability: str | None = Field(default=None, description="Optional capability key")


class AgentRunResponse(BaseModel):
    result: str


class ContractAnalysisResponse(BaseModel):
    filename: str
    result: str


class ChatSessionResponse(BaseModel):
    session_id: str


class ChatMessageItem(BaseModel):
    role: str
    content: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageItem]


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Chat session id")
    message: str = Field(..., min_length=1, description="User chat message")


class ChatReference(BaseModel):
    id: str
    title: str


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessageItem
    intent: str
    references: list[ChatReference]


class FeedbackRequest(BaseModel):
    target: str = Field(..., min_length=1, description="Feedback target area")
    rating: str = Field(..., pattern="^(like|dislike)$", description="Feedback rating")
    capability: str | None = Field(default=None, description="Related capability key")
    prompt: str | None = Field(default=None, description="User prompt")
    result_preview: str | None = Field(default=None, description="Short result preview")


class FeedbackResponse(BaseModel):
    status: str
    count: int
